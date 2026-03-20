import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Vercel environment detection
IS_VERCEL = os.getenv("VERCEL") == "1"

# Database
if IS_VERCEL:
    DATABASE_PATH = Path("/tmp/books.db")
    SEARCH_INDEX_PATH = Path("/tmp/search_index")
    OUTPUT_DIR = Path("/tmp/generated")
    BOOKS_DIR = BASE_DIR / "books"  # Books should be read-only in the repo
else:
    DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/books.db")
    SEARCH_INDEX_PATH = BASE_DIR / os.getenv("SEARCH_INDEX_PATH", "data/search_index")
    OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "data/generated")
    BOOKS_DIR = BASE_DIR / os.getenv("BOOKS_DIR", "books")

# Ensure directories exist
if not IS_VERCEL:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_INDEX_PATH.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    BOOKS_DIR.mkdir(parents=True, exist_ok=True)
    (BOOKS_DIR / "uzbek").mkdir(exist_ok=True)
    (BOOKS_DIR / "russian").mkdir(exist_ok=True)
else:
    # On Vercel, only create /tmp directories
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    SEARCH_INDEX_PATH.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
