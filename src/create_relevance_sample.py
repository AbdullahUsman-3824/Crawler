
import csv
import random
import sqlite3
from collections import defaultdict

from src.config import DATA_DIR

DB_FILE = DATA_DIR / "raw" / "iio_comments.sqlite3"
OUTPUT_DIR = DATA_DIR / "processed"

SAMPLE_FILE = OUTPUT_DIR / "relevance_sample_pilot.csv"
STATS_FILE = OUTPUT_DIR / "relevance_sample_stats.csv"

SEED = 42
PER_VIDEO = 4
PER_TYPE = 2  # Target: 2 top-level + 2 replies per video


def create_sample():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if not DB_FILE.exists():
        raise FileNotFoundError(f"Database not found: {DB_FILE}")

    randomizer = random.Random(SEED)

    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row

    rows = connection.execute("""
        SELECT
            c.comment_id,
            c.video_id,
            v.title AS video_title,
            c.parent_comment_id,
            c.comment_type,
            c.comment_text,
            c.published_at,
            c.like_count
        FROM comments c
        LEFT JOIN video_collection v
            ON c.video_id = v.video_id
        WHERE c.comment_text IS NOT NULL
          AND TRIM(c.comment_text) != ''
        ORDER BY c.video_id
    """).fetchall()

    connection.close()

    videos = defaultdict(lambda: {
        "top_level": [],
        "reply": []
    })

    for row in rows:
        videos[row["video_id"]][row["comment_type"]].append(dict(row))

    selected = []

    for video_id, groups in videos.items():
        top_level = groups["top_level"][:]
        replies = groups["reply"][:]

        randomizer.shuffle(top_level)
        randomizer.shuffle(replies)

        # First, select up to 2 from each comment type.
        chosen = (
            top_level[:PER_TYPE]
            + replies[:PER_TYPE]
        )

        # If one type has fewer than 2, fill from the other.
        remaining = PER_VIDEO - len(chosen)

        if remaining > 0:
            unused = (
                top_level[PER_TYPE:]
                + replies[PER_TYPE:]
            )
            randomizer.shuffle(unused)
            chosen.extend(unused[:remaining])

        selected.extend(chosen)

    randomizer.shuffle(selected)

    annotation_fields = [
        "relevance_label",
        "context_type",
        "reason",
        "evidence_text",
        "reviewer_notes"
    ]

    fieldnames = [
        "comment_id",
        "video_id",
        "video_title",
        "parent_comment_id",
        "comment_type",
        "comment_text",
        "published_at",
        "like_count",
        *annotation_fields
    ]

    with open(SAMPLE_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writeheader()

        for row in selected:
            output = {key: row.get(key) for key in fieldnames}
            for field in annotation_fields:
                output[field] = ""
            writer.writerow(output)

    # Summary by video and comment type.
    stats = defaultdict(lambda: {
        "video_title": "",
        "top_level": 0,
        "reply": 0,
        "total": 0
    })

    for row in selected:
        item = stats[row["video_id"]]
        item["video_title"] = row["video_title"] or ""
        item[row["comment_type"]] += 1
        item["total"] += 1

    with open(STATS_FILE, "w", newline="", encoding="utf-8-sig") as file:
        fields = [
            "video_id",
            "video_title",
            "top_level",
            "reply",
            "total"
        ]

        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for video_id, item in sorted(stats.items()):
            writer.writerow({
                "video_id": video_id,
                **item
            })

    print("========== RELEVANCE SAMPLE ==========")
    print(f"Total comments in sample: {len(selected)}")
    print(f"Videos represented: {len(stats)}")
    print(f"Top-level comments: {sum(x['top_level'] for x in stats.values())}")
    print(f"Replies: {sum(x['reply'] for x in stats.values())}")
    print(f"\nSample saved: {SAMPLE_FILE}")
    print(f"Statistics saved: {STATS_FILE}")


if __name__ == "__main__":
    create_sample()
