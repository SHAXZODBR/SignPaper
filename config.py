import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Database
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/books.db")

# Search
SEARCH_INDEX_PATH = BASE_DIR / os.getenv("SEARCH_INDEX_PATH", "data/search_index")

# Books
BOOKS_DIR = BASE_DIR / os.getenv("BOOKS_DIR", "books")

# Output
OUTPUT_DIR = BASE_DIR / os.getenv("OUTPUT_DIR", "data/generated")

# Features
ENABLE_SEMANTIC_SEARCH = os.getenv("ENABLE_SEMANTIC_SEARCH", "false").lower() == "true"

# Ensure directories exist
DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
SEARCH_INDEX_PATH.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
BOOKS_DIR.mkdir(parents=True, exist_ok=True)
(BOOKS_DIR / "uzbek").mkdir(exist_ok=True)
(BOOKS_DIR / "russian").mkdir(exist_ok=True)
