# -*- coding: utf-8 -*-
"""
Update database PDF paths to Supabase Storage URLs.
Maps local filenames to Supabase Storage files.
"""
import os
import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
BUCKET_NAME = "books"

client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("Mapping Supabase Storage files")
print("=" * 60)

# Build file map recursively
file_map = {}  # filename -> full URL

def scan_folder(path=""):
    """Scan folder and add files to map."""
    try:
        items = client.storage.from_(BUCKET_NAME).list(path)
        for item in items:
            name = item.get('name', '')
            full_path = f"{path}/{name}" if path else name
            
            if item.get('id'):  # It's a file
                url = client.storage.from_(BUCKET_NAME).get_public_url(full_path)
                # Store by filename (lowercase, without extension variations)
                key = name.lower()
                file_map[key] = url
                # Also store by full path
                file_map[full_path.lower()] = url
            else:  # It's a folder
                scan_folder(full_path)
    except Exception as e:
        print(f"  Error scanning {path}: {e}")

# Scan uzbek and russian folders
print("\n[1] Scanning Supabase Storage...")
scan_folder("uzbek")
scan_folder("russian")
print(f"   Found {len(file_map)} files")

if len(file_map) == 0:
    print("   ERROR: No files found in storage!")
    sys.exit(1)

# Show sample
print("\n   Sample files:")
count = 0
for key, url in file_map.items():
    if count < 5:
        print(f"     {key}: {url[:70]}...")
        count += 1

# Get all books
print("\n[2] Getting books from database...")
books = client.table("books").select("*").execute()
print(f"   Found {len(books.data)} books")

# Update paths
print("\n[3] Updating paths...")
updated = 0
not_found = 0

for book in books.data:
    book_id = book['id']
    pdf_uz = book.get('pdf_path_uz') or ""
    pdf_ru = book.get('pdf_path_ru') or ""
    
    update_data = {}
    
    # Handle UZ path
    if pdf_uz and ('\\' in pdf_uz or pdf_uz.startswith('c:')):
        filename = pdf_uz.split('\\')[-1].lower()
        if filename in file_map:
            update_data['pdf_path_uz'] = file_map[filename]
    
    # Handle RU path
    if pdf_ru and ('\\' in pdf_ru or pdf_ru.startswith('c:')):
        filename = pdf_ru.split('\\')[-1].lower()
        if filename in file_map:
            update_data['pdf_path_ru'] = file_map[filename]
    
    if update_data:
        try:
            client.table("books").update(update_data).eq("id", book_id).execute()
            updated += 1
            print(f"   Updated book {book_id}")
        except Exception as e:
            print(f"   Error book {book_id}: {e}")
    else:
        not_found += 1

print(f"\n[4] Summary:")
print(f"   Updated: {updated} books")
print(f"   Not matched: {not_found} books")

# Verify
print("\n[5] Sample updated paths:")
sample = client.table("books").select("id, title_uz, pdf_path_uz").limit(5).execute()
for b in sample.data:
    path = b.get('pdf_path_uz') or 'None'
    is_url = 'supabase' in path.lower() if path else False
    status = "OK" if is_url else "LOCAL" if path != 'None' else "EMPTY"
    print(f"   Book {b['id']}: [{status}] {path[:60]}...")
