# Check large local books
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

BASE_DIR = r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"
client = create_client(SUPABASE_URL, SUPABASE_KEY)

books = client.table("books").select("id, title_uz, pdf_path_uz").execute().data
local_books = [b for b in books if not b.get('pdf_path_uz') or 'supabase' not in b.get('pdf_path_uz', '')]

print(f"Checking {len(local_books)} local/missing books for size...")
large_files = []

for b in local_books:
    path = b.get('pdf_path_uz')
    if path and os.path.exists(path):
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > 50:
            large_files.append((b['id'], b['title_uz'], size_mb, path))
    else:
        # Search for it in the books folder if the path is invalid
        pass

print("\nLarge files (>50MB):")
for fid, title, size, path in large_files:
    print(f"ID {fid}: {title} | {size:.1f} MB | {path}")

print(f"\nTotal large files: {len(large_files)}")
