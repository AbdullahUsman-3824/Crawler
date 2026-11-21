import csv
import json
from pathlib import Path

from googleapiclient.errors import HttpError

from src.config import DATA_DIR
from src.youtube_client import create_youtube_client

INPUT_FILE = DATA_DIR / "raw" / "discovered_videos.json"

OUTPUT_JSON = DATA_DIR / "processed" / "validated_pilot1.json"
OUTPUT_CSV = DATA_DIR / "processed" / "validated_pilot1.csv"

BATCH_SIZE = 50


def extract_error_reason(error):
    """Extract the API error reason and message."""
    try:
        payload = json.loads(error.content.decode("utf-8"))
        errors = payload.get("error", {}).get("errors", [])

        if errors:
            return (errors[0].get("reason", ""), errors[0].get("message", ""))

        return "", payload.get("error", {}).get("message", "")

    except (ValueError, AttributeError):
        return "", str(error)


def load_discovered_videos():
    if not INPUT_FILE.exists():
        raise FileNotFoundError(f"Discovery file not found: {INPUT_FILE}")

    with open(INPUT_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_results(videos):
    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as file:
        json.dump(videos, file, ensure_ascii=False, indent=2)

    if videos:
        fieldnames = list(videos[0].keys())

        with open(OUTPUT_CSV, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(videos)

    print(f"Saved {len(videos)} validated video records.")


def get_video_metadata(youtube, video_ids):
    """
    Fetch metadata for up to 50 videos in one API request.
    """
    response = (
        youtube.videos()
        .list(
            part="snippet,statistics,contentDetails,status",
            id=",".join(video_ids),
            maxResults=BATCH_SIZE,
        )
        .execute()
    )

    return response.get("items", [])


def check_comment_availability(youtube, video_id):
    """
    Probe one comment thread to determine whether comments
    can be retrieved.

    This is a lightweight availability check, not collection.
    """

    try:
        response = (
            youtube.commentThreads()
            .list(part="id", videoId=video_id, maxResults=1)
            .execute()
        )

        if response.get("items"):
            return "available"

        return "no_comments_found"

    except HttpError as error:
        reason, message = extract_error_reason(error)
        message_lower = message.lower()

        if reason == "commentsDisabled" or "comments are disabled" in message_lower:
            return "disabled"

        if reason in ("videoNotFound", "notFound"):
            return "unavailable"

        if reason in ("quotaExceeded", "dailyLimitExceeded"):
            return "quota_exhausted"

        if reason in ("forbidden", "forbiddenCommenting"):
            return "forbidden_or_restricted"

        return f"probe_error:{reason or error.resp.status}"


def validate_discovered_videos(probe_comments=True):
    youtube = create_youtube_client()
    discovered = load_discovered_videos()

    if not discovered:
        print("No discovered videos found.")
        return []

    print(f"Videos to validate: {len(discovered)}")

    # Preserve original discovery information.
    discovered_by_id = {video["video_id"]: video for video in discovered}

    video_ids = list(discovered_by_id.keys())

    validated = []
    found_ids = set()
    failed_metadata_ids = set()

    # Fetch metadata in batches.
    for start in range(0, len(video_ids), BATCH_SIZE):
        batch = video_ids[start : start + BATCH_SIZE]

        print(f"\nFetching metadata: " f"{start + 1}-{start + len(batch)}")

        try:
            items = get_video_metadata(youtube, batch)

        except HttpError as error:
            reason, message = extract_error_reason(error)
            failed_metadata_ids.update(batch)

            print(f"Metadata request failed: {reason} {message}")

            if reason in ("quotaExceeded", "dailyLimitExceeded"):
                print("Stopping because API quota is exhausted.")
                break

            continue

        for item in items:
            video_id = item["id"]
            found_ids.add(video_id)

            snippet = item.get("snippet", {})
            statistics = item.get("statistics", {})
            content = item.get("contentDetails", {})
            status = item.get("status", {})

            original = discovered_by_id[video_id]

            record = {
                **original,
                "availability": "available",
                "published_at": snippet.get(
                    "publishedAt", original.get("published_at", "")
                ),
                "title": snippet.get("title", original.get("title", "")),
                "description": snippet.get(
                    "description", original.get("description", "")
                ),
                "view_count": statistics.get("viewCount"),
                "like_count": statistics.get("likeCount"),
                "comment_count": statistics.get("commentCount"),
                "duration": content.get("duration"),
                "definition": content.get("definition"),
                "caption_available": content.get("caption"),
                "privacy_status": status.get("privacyStatus"),
                "embeddable": status.get("embeddable"),
                "comment_availability": "not_checked",
            }

            validated.append(record)

        # Save after every metadata batch.
        save_results(validated)

    # IDs not returned by videos.list are unavailable to this API request.
    for video_id in video_ids:
        if video_id not in found_ids:
            original = discovered_by_id[video_id]

            validated.append(
                {
                    **original,
                    "availability": (
                        "metadata_check_failed"
                        if video_id in failed_metadata_ids
                        else "not_returned_by_api"
                    ),
                    "view_count": None,
                    "like_count": None,
                    "comment_count": None,
                    "duration": None,
                    "definition": None,
                    "caption_available": None,
                    "privacy_status": None,
                    "embeddable": None,
                    "comment_availability": "not_checked",
                }
            )

    save_results(validated)

    # Probe comment availability separately.
    if probe_comments:
        print("\nChecking comment availability...")

        for index, record in enumerate(validated, start=1):
            if record["availability"] != "available":
                continue

            if record["comment_availability"] != "not_checked":
                continue

            video_id = record["video_id"]

            print(f"[{index}/{len(validated)}] " f"Checking {video_id}...")

            result = check_comment_availability(youtube, video_id)

            record["comment_availability"] = result

            # Save after every probe to preserve progress.
            save_results(validated)

            if result == "quota_exhausted":
                print("Stopping comment checks due to quota exhaustion.")
                break

    print("\nValidation summary:")

    total = len(validated)
    available = sum(v["availability"] == "available" for v in validated)
    unavailable = total - available

    comments_available = sum(
        v["comment_availability"] == "available" for v in validated
    )
    comments_disabled = sum(v["comment_availability"] == "disabled" for v in validated)
    no_comments = sum(
        v["comment_availability"] == "no_comments_found" for v in validated
    )

    print(f"Total videos:       {total}")
    print(f"Available videos:   {available}")
    print(f"Unavailable videos: {unavailable}")
    print(f"Comments available: {comments_available}")
    print(f"Comments disabled:  {comments_disabled}")
    print(f"No comments found:  {no_comments}")

    print(f"\nJSON: {OUTPUT_JSON}")
    print(f"CSV:  {OUTPUT_CSV}")

    return validated
