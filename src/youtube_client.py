
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from src.config import YOUTUBE_API_KEY


def create_youtube_client():
    return build(
        "youtube",
        "v3",
        developerKey=YOUTUBE_API_KEY,
        cache_discovery=False
    )


def test_connection():
    youtube = create_youtube_client()

    try:
        response = youtube.i18nLanguages().list(
            part="snippet"
        ).execute()

        languages = response.get("items", [])

        print("YouTube API connection successful!")
        print(f"Available languages returned: {len(languages)}")

        return True

    except HttpError as error:
        print("YouTube API request failed.")
        print(f"HTTP status: {error.resp.status}")
        print(error.content.decode("utf-8", errors="replace"))
        return False
