
import os
from pathlib import Path
from dotenv import load_dotenv

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

CODEBOOK_PATH = BASE_DIR / "config" / "codebook.json"
DATA_DIR = BASE_DIR / "data"

if not YOUTUBE_API_KEY:
    raise RuntimeError(
        "YOUTUBE_API_KEY is missing. Check your .env file."
    )

if not CODEBOOK_PATH.exists():
    raise FileNotFoundError(
        f"Codebook not found: {CODEBOOK_PATH}"
    )
