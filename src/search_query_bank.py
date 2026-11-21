import csv
from pathlib import Path

from src.config import BASE_DIR

QUERY_FILE = BASE_DIR / "config" / "search_queries.csv"


def load_search_queries(pilot_batch="Pilot 1"):
    if not QUERY_FILE.exists():
        raise FileNotFoundError(QUERY_FILE)

    queries = []

    with open(QUERY_FILE, "r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        for row in reader:
            if row["pilot_batch"] != pilot_batch:
                continue

            queries.append(
                {
                    "query_id": row["query_id"],
                    "query": row["search_query"],
                    "group": row["query_group"],
                    "focus": row["codebook_focus"],
                    "priority": row["priority"],
                }
            )

    return queries
