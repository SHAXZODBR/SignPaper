# -*- coding: utf-8 -*-
"""
Update database PDF paths to use Supabase Storage URLs.
Matches local filenames to files in Supabase Storage bucket.
"""
import os
import sys
import codecs
import re
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
print("Updating PDF paths to Supabase Storage URLs")
print("=" * 60)

# Get list of files in the books bucket
print("\n[1] Listing files in Supabase Storage bucket...")
try:
    # List all folders first
    folders = client.storage.from_(BUCKET_NAME).list()
    print(f"   Found {len(folders)} items in root")
    
    # Build a map of filenames to URLs
    file_map = {}
    
    for folder in folders:
        folder_name = folder.get('name')
        if folder.get('id') is None:  # It's a folder
            # List files in folder
            files = client.storage.from_(BUCKET_NAME).list(folder_name)
            for f in files:
                if f.get('id'):  # It's a file
                    file_name = f.get('name')
                    full_path = f"{folder_name}/{file_name}"
                    # Create public URL
                    public_url = client.storage.from_(BUCKET_NAME).get_public_url(full_path)
                    file_map[file_name.lower()] = public_url
                    file_map[full_path.lower()] = public_url
except Exception as e:
    print(f"   Error: {e}")
    file_map = {}

print(f"   Total files mapped: {len(file_map)}")

# Show sample
if file_map:
    sample = list(file_map.items())[:3]
    print("   Sample files:")
    for name, url in sample:
        print(f"     {name}: {url[:60]}...")

# Get all books
print("\n[2] Getting books from database...")
books = client.table("books").select("*").execute()
print(f"   Found {len(books.data)} books")

# Update paths
print("\n[3] Updating paths...")
updated = 0

for book in books.data:
    book_id = book['id']
    pdf_uz = book.get('pdf_path_uz') or ""
    pdf_ru = book.get('pdf_path_ru') or ""
    
    update_data = {}
    
    # Check if path is a local path (contains backslash or c:)
    if pdf_uz and ('\\' in pdf_uz or pdf_uz.startswith('c:')):
        # Extract filename
        filename = pdf_uz.split('\\')[-1].lower()
        if filename in file_map:
            update_data['pdf_path_uz'] = file_map[filename]
        else:
            # Try to find by partial match
            for key, url in file_map.items():
                if filename in key or key in filename:
                    update_data['pdf_path_uz'] = url
                    break
    
    if pdf_ru and ('\\' in pdf_ru or pdf_ru.startswith('c:')):
        filename = pdf_ru.split('\\')[-1].lower()
        if filename in file_map:
            update_data['pdf_path_ru'] = file_map[filename]
        else:
            for key, url in file_map.items():
                if filename in key or key in filename:
                    update_data['pdf_path_ru'] = url
                    break
    
    if update_data:
        try:
            client.table("books").update(update_data).eq("id", book_id).execute()
            updated += 1
            print(f"   Updated book {book_id}")
        except Exception as e:
            print(f"   Error updating book {book_id}: {e}")

print(f"\n[4] Done! Updated {updated} books")

# Verify
print("\n[5] Verification - Sample updated paths:")
sample_books = client.table("books").select("id, pdf_path_uz, pdf_path_ru").limit(3).execute()
for b in sample_books.data:
    path = b.get('pdf_path_uz') or b.get('pdf_path_ru') or 'None'
    print(f"   Book {b['id']}: {path[:80]}...")
