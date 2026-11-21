import csv
import random
import sqlite3
from collections import Counter
from pathlib import Path

from src.config import DATA_DIR

DB_FILE = DATA_DIR / "raw" / "iio_comments.sqlite3"
OUTPUT_DIR = DATA_DIR / "processed"

SAMPLE_FILE = OUTPUT_DIR / "comment_audit_sample.csv"
STATS_FILE = OUTPUT_DIR / "comment_audit_stats.csv"


def run_audit():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_FILE)
    connection.row_factory = sqlite3.Row

    # Overall statistics
    total = connection.execute("SELECT COUNT(*) FROM comments").fetchone()[0]

    type_counts = connection.execute("""
        SELECT comment_type, COUNT(*) AS total
        FROM comments
        GROUP BY comment_type
    """).fetchall()

    video_counts = connection.execute("""
        SELECT video_id, COUNT(*) AS total
        FROM comments
        GROUP BY video_id
        ORDER BY total DESC
    """).fetchall()

    empty = connection.execute("""
        SELECT COUNT(*)
        FROM comments
        WHERE comment_text IS NULL
           OR TRIM(comment_text) = ''
    """).fetchone()[0]

    short = connection.execute("""
        SELECT COUNT(*)
        FROM comments
        WHERE LENGTH(TRIM(comment_text)) < 10
    """).fetchone()[0]

    duplicate_text = connection.execute("""
        SELECT COUNT(*) FROM (
            SELECT LOWER(TRIM(comment_text))
            FROM comments
            WHERE TRIM(comment_text) != ''
            GROUP BY LOWER(TRIM(comment_text))
            HAVING COUNT(*) > 1
        )
    """).fetchone()[0]

    print("\n========== DATASET AUDIT ==========")
    print(f"Total comments: {total:,}")
    print(f"Empty comments: {empty:,}")
    print(f"Short comments (<10 chars): {short:,}")
    print(f"Repeated text groups: {duplicate_text:,}")
    print(f"Videos represented: {len(video_counts)}")

    for row in type_counts:
        print(f"{row['comment_type']}: {row['total']:,}")

    print("\nTop 10 videos by comment count:")
    for row in video_counts[:10]:
        print(f"{row['video_id']}: {row['total']:,}")

    # Stratified sample: 50 top-level + 50 replies
    random.seed(42)
    samples = []

    for comment_type in ["top_level", "reply"]:
        rows = connection.execute(
            """
            SELECT *
            FROM comments
            WHERE comment_type = ?
            ORDER BY RANDOM()
            LIMIT 50
        """,
            (comment_type,),
        ).fetchall()

        samples.extend([dict(row) for row in rows])

    random.shuffle(samples)

    fields = [
        "comment_id",
        "video_id",
        "parent_comment_id",
        "comment_type",
        "comment_text",
        "published_at",
        "like_count",
    ]

    with open(SAMPLE_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()

        for sample in samples:
            writer.writerow({key: sample.get(key) for key in fields})

    # Save summary statistics
    stats = [
        ("Total comments", total),
        ("Empty comments", empty),
        ("Short comments", short),
        ("Repeated text groups", duplicate_text),
        ("Videos represented", len(video_counts)),
    ]

    with open(STATS_FILE, "w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow(["Metric", "Value"])
        writer.writerows(stats)

    connection.close()

    print(f"\nSample: {SAMPLE_FILE}")
    print(f"Stats:  {STATS_FILE}")


if __name__ == "__main__":
    run_audit()
