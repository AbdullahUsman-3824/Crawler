import csv
import json
from pathlib import Path

from googleapiclient.errors import HttpError

from src.config import DATA_DIR
from src.youtube_client import create_youtube_client

# Initial research queries.
# We'll expand and refine these after inspecting the first results.
SEARCH_QUERIES = [
    "AI deepfake financial scam",
    "AI voice cloning scam",
    "CEO fraud business email impersonation",
    "fake bank officer financial scam",
    "online investment fraud guaranteed returns",
    "crypto investment scam victim",
    "urgent payment impersonation scam",
    "how to report online financial fraud",
    "deepfake scam awareness and prevention",
    "AI voice scam Pakistan",
    "online fraud Pakistan Urdu",
    "bank account scam Pakistan",
]

CHECKPOINT_FILE = DATA_DIR / "checkpoints" / "video_discovery.json"
JSON_OUTPUT = DATA_DIR / "raw" / "discovered_videos.json"
CSV_OUTPUT = DATA_DIR / "raw" / "discovered_videos.csv"


def load_checkpoint():
    if not CHECKPOINT_FILE.exists():
        return set(), {}

    with open(CHECKPOINT_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)

    completed = set(data.get("completed_queries", []))
    videos = data.get("videos", {})

    return completed, videos


def save_checkpoint(completed_queries, videos):
    CHECKPOINT_FILE.parent.mkdir(parents=True, exist_ok=True)

    data = {"completed_queries": sorted(completed_queries), "videos": videos}

    with open(CHECKPOINT_FILE, "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def save_results(videos):
    JSON_OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    records = list(videos.values())

    with open(JSON_OUTPUT, "w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

    if records:
        with open(CSV_OUTPUT, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.DictWriter(file, fieldnames=records[0].keys())
            writer.writeheader()
            writer.writerows(records)

    print(f"\nSaved {len(records)} unique videos.")
    print(f"JSON: {JSON_OUTPUT}")
    print(f"CSV:  {CSV_OUTPUT}")


def discover_videos(queries=None, max_results=10, max_pages_per_query=1):
    """
    Discover videos using YouTube search.list.

    max_results: 1-50 results per API request.
    max_pages_per_query: maximum pages requested for each query.
    """

    queries = queries or SEARCH_QUERIES

    if not 1 <= max_results <= 50:
        raise ValueError("max_results must be between 1 and 50.")

    if max_pages_per_query < 1:
        raise ValueError("max_pages_per_query must be at least 1.")

    youtube = create_youtube_client()
    completed_queries, videos = load_checkpoint()

    print(f"Previously discovered videos: {len(videos)}")
    print(f"Completed queries: {len(completed_queries)}")

    for query in queries:
        if query in completed_queries:
            print(f"\nSkipping completed query: {query}")
            continue

        print(f"\nSearching: {query}")

        page_token = None

        try:
            for page in range(max_pages_per_query):
                request = youtube.search().list(
                    part="snippet",
                    q=query,
                    type="video",
                    order="relevance",
                    maxResults=max_results,
                    pageToken=page_token,
                )

                response = request.execute()

                for item in response.get("items", []):
                    video_id = item["id"].get("videoId")

                    if not video_id:
                        continue

                    snippet = item.get("snippet", {})

                    record = {
                        "video_id": video_id,
                        "title": snippet.get("title", ""),
                        "description": snippet.get("description", ""),
                        "channel_id": snippet.get("channelId", ""),
                        "channel_title": snippet.get("channelTitle", ""),
                        "published_at": snippet.get("publishedAt", ""),
                        "thumbnail_url": (
                            snippet.get("thumbnails", {}).get("high", {}).get("url", "")
                        ),
                        "video_url": f"https://www.youtube.com/watch?v={video_id}",
                        "discovery_queries": [],
                    }

                    if video_id not in videos:
                        videos[video_id] = record

                    if query not in videos[video_id]["discovery_queries"]:
                        videos[video_id]["discovery_queries"].append(query)

                page_token = response.get("nextPageToken")

                print(
                    f"  Page {page + 1}: " f"{len(response.get('items', []))} results"
                )

                if not page_token:
                    break

            completed_queries.add(query)

            # Save after every query so interrupted runs can resume.
            save_checkpoint(completed_queries, videos)
            save_results(videos)

        except HttpError as error:
            print(f"\nYouTube API error for query: {query}")
            print(f"HTTP status: {error.resp.status}")
            print(error.content.decode("utf-8", errors="replace"))
            print("Stopping discovery. Completed work is checkpointed.")
            break

    save_checkpoint(completed_queries, videos)
    save_results(videos)

    return list(videos.values())
