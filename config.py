import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Telegram
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rhjsndgajlvnhbzwayhc.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A")

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
