import csv
import html
import json
import re
import sqlite3
import sys

from pathlib import Path

from googleapiclient.errors import HttpError

from src.config import DATA_DIR
from src.youtube_client import create_youtube_client

VIDEO_FILE = DATA_DIR / "processed" / "validated_pilot1.csv"

DB_FILE = DATA_DIR / "raw" / "iio_comments.sqlite3"
CSV_OUTPUT = DATA_DIR / "raw" / "collected_comments.csv"

PAGE_SIZE = 100


def safe_console_text(text):
    encoding = getattr(sys.stdout, "encoding", None) or "utf-8"
    return str(text).encode(encoding, errors="backslashreplace").decode(encoding)


def clean_text(text):
    """Convert HTML-formatted comment text into readable text."""
    text = re.sub(r"<br\s*/?>", "\n", text or "", flags=re.I)
    text = re.sub(r"<[^>]+>", "", text)
    return html.unescape(text).strip()


def get_error_details(error):
    try:
        payload = json.loads(error.content.decode("utf-8"))
        details = payload.get("error", {})
        errors = details.get("errors", [])

        reason = errors[0].get("reason", "") if errors else ""
        message = details.get("message", "")

        return reason, message

    except (ValueError, AttributeError):
        return "", str(error)


def initialize_database():
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_FILE)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS comments (
            comment_id TEXT PRIMARY KEY,
            video_id TEXT NOT NULL,
            parent_comment_id TEXT,
            comment_type TEXT NOT NULL,
            comment_text TEXT,
            published_at TEXT,
            updated_at TEXT,
            like_count INTEGER DEFAULT 0,
            total_reply_count INTEGER DEFAULT 0
        )
    """)

    connection.execute("""
        CREATE INDEX IF NOT EXISTS idx_comments_video
        ON comments(video_id)
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS video_collection (
            video_id TEXT PRIMARY KEY,
            title TEXT,
            reported_comment_count INTEGER,
            collection_status TEXT DEFAULT 'pending',
            collected_comments INTEGER DEFAULT 0,
            error_message TEXT
        )
    """)

    connection.commit()
    return connection


def load_candidate_videos():
    if not VIDEO_FILE.exists():
        raise FileNotFoundError(
            f"Validated video file not found: {VIDEO_FILE}\n"
            "Run discovery and validation first:\n"
            "  python -m src.main\n"
            "  python -m src.validate_discovery\n"
            "Then rerun collection:\n"
            "  python -m src.comment_collector"
        )

    candidates = []

    with open(VIDEO_FILE, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row.get("availability") != "available":
                continue

            raw_count = row.get("comment_count", "").strip()

            # Positive counts and unknown counts are candidates.
            # Explicit zero counts are skipped in this first pass.
            if raw_count:
                try:
                    if int(float(raw_count)) == 0:
                        continue
                    reported_count = int(float(raw_count))
                except ValueError:
                    reported_count = None
            else:
                reported_count = None

            candidates.append(
                {
                    "video_id": row["video_id"],
                    "title": row.get("title", ""),
                    "reported_comment_count": reported_count,
                }
            )

    return candidates


def save_comment(
    connection,
    video_id,
    comment,
    comment_type,
    parent_comment_id=None,
    total_reply_count=0,
):

    snippet = comment.get("snippet", {})

    text = clean_text(snippet.get("textOriginal") or snippet.get("textDisplay") or "")

    connection.execute(
        """
        INSERT OR IGNORE INTO comments (
            comment_id,
            video_id,
            parent_comment_id,
            comment_type,
            comment_text,
            published_at,
            updated_at,
            like_count,
            total_reply_count
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        (
            comment["id"],
            video_id,
            parent_comment_id,
            comment_type,
            text,
            snippet.get("publishedAt"),
            snippet.get("updatedAt"),
            snippet.get("likeCount", 0),
            total_reply_count,
        ),
    )


def collect_remaining_replies(
    youtube, connection, video_id, parent_id, total_replies, included_replies
):
    """
    Fetch replies omitted from commentThreads.list.
    The primary key prevents duplicate insertion.
    """

    if total_replies <= included_replies:
        return True

    page_token = None

    while True:
        response = (
            youtube.comments()
            .list(
                part="snippet",
                parentId=parent_id,
                maxResults=PAGE_SIZE,
                pageToken=page_token,
            )
            .execute()
        )

        for reply in response.get("items", []):
            save_comment(
                connection, video_id, reply, "reply", parent_comment_id=parent_id
            )

        connection.commit()

        page_token = response.get("nextPageToken")

        if not page_token:
            break

    return True


def collect_video_comments(youtube, connection, video):
    video_id = video["video_id"]
    page_token = None

    while True:
        response = (
            youtube.commentThreads()
            .list(
                part="snippet,replies",
                videoId=video_id,
                maxResults=PAGE_SIZE,
                order="time",
                pageToken=page_token,
                textFormat="plainText",
            )
            .execute()
        )

        for thread in response.get("items", []):
            thread_snippet = thread.get("snippet", {})
            top_comment = thread_snippet.get("topLevelComment", {})

            if not top_comment:
                continue

            parent_id = top_comment["id"]
            total_replies = thread_snippet.get("totalReplyCount", 0)

            save_comment(
                connection,
                video_id,
                top_comment,
                "top_level",
                total_reply_count=total_replies,
            )

            included_replies = 0

            for reply in thread.get("replies", {}).get("comments", []):
                save_comment(
                    connection, video_id, reply, "reply", parent_comment_id=parent_id
                )
                included_replies += 1

            # Fetch any replies not included in the thread response.
            collect_remaining_replies(
                youtube,
                connection,
                video_id,
                parent_id,
                total_replies,
                included_replies,
            )

        # Save every page. An interruption won't lose previous pages.
        connection.commit()

        page_token = response.get("nextPageToken")

        if not page_token:
            break


def mark_video(connection, video_id, status, error_message=None):
    count = connection.execute(
        "SELECT COUNT(*) FROM comments WHERE video_id = ?", (video_id,)
    ).fetchone()[0]

    connection.execute(
        """
        UPDATE video_collection
        SET collection_status = ?,
            collected_comments = ?,
            error_message = ?
        WHERE video_id = ?
    """,
        (status, count, error_message, video_id),
    )

    connection.commit()


def export_comments(connection):
    CSV_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    cursor = connection.execute("""
        SELECT
            comment_id,
            video_id,
            parent_comment_id,
            comment_type,
            comment_text,
            published_at,
            updated_at,
            like_count,
            total_reply_count
        FROM comments
        ORDER BY video_id, published_at
    """)

    headers = [column[0] for column in cursor.description]

    with open(CSV_OUTPUT, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(cursor.fetchall())

    print(f"Exported comments to: {CSV_OUTPUT}")


def run_collection():
    youtube = create_youtube_client()
    connection = initialize_database()

    videos = load_candidate_videos()

    print(f"Candidate videos: {len(videos)}")

    for video in videos:
        video_id = video["video_id"]

        connection.execute(
            """
            INSERT OR IGNORE INTO video_collection (
                video_id, title, reported_comment_count
            )
            VALUES (?, ?, ?)
        """,
            (video_id, video["title"], video["reported_comment_count"]),
        )

    connection.commit()

    for index, video in enumerate(videos, start=1):
        video_id = video["video_id"]

        status = connection.execute(
            "SELECT collection_status FROM video_collection WHERE video_id = ?",
            (video_id,),
        ).fetchone()[0]

        if status == "completed":
            print(f"[{index}/{len(videos)}] Skipping completed: {video_id}")
            continue

        print(
            f"\n[{index}/{len(videos)}] "
            f"Collecting: {safe_console_text(video['title'][:70])}"
        )

        try:
            collect_video_comments(youtube, connection, video)

            mark_video(connection, video_id, "completed")

            print(f"Completed: {video_id}")

        except HttpError as error:
            reason, message = get_error_details(error)

            print(f"API error for {video_id}: {reason} {message}")

            if reason in ("quotaExceeded", "dailyLimitExceeded"):
                mark_video(connection, video_id, "quota_exhausted", message)
                print("Quota exhausted. Stopping safely.")
                break

            if reason in ("commentsDisabled", "forbiddenCommenting"):
                mark_video(connection, video_id, "comments_disabled", message)
            else:
                mark_video(connection, video_id, "error", message)

        except Exception as error:
            print(f"Unexpected error for {video_id}: {error}")

            mark_video(connection, video_id, "error", str(error))

        export_comments(connection)

    export_comments(connection)

    total = connection.execute("SELECT COUNT(*) FROM comments").fetchone()[0]

    top_level = connection.execute(
        "SELECT COUNT(*) FROM comments WHERE comment_type = 'top_level'"
    ).fetchone()[0]

    replies = connection.execute(
        "SELECT COUNT(*) FROM comments WHERE comment_type = 'reply'"
    ).fetchone()[0]

    print("\nCollection summary")
    print(f"Unique comments: {total}")
    print(f"Top-level comments: {top_level}")
    print(f"Replies: {replies}")
    print(f"Database: {DB_FILE}")

    connection.close()


if __name__ == "__main__":
    run_collection()

