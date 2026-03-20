# -*- coding: utf-8 -*-
"""
Direct update of ALL book paths to Supabase Storage URLs.
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

client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 60)
print("DIRECT UPDATE - All Books to Supabase URLs")
print("=" * 60)

# Step 1: Get all files from storage
print("\n[1] Getting files from Supabase Storage...")
all_files = {}

def scan(path=""):
    try:
        items = client.storage.from_("books").list(path)
        for item in items:
            name = item.get('name', '')
            full_path = f"{path}/{name}" if path else name
            if item.get('id'):  # File
                url = client.storage.from_("books").get_public_url(full_path)
                # Store by filename
                key = name.lower().replace(' ', '_')
                all_files[key] = url
                all_files[name.lower()] = url
            else:
                scan(full_path)
    except Exception as e:
        print(f"  Error: {e}")

scan("uzbek")
scan("russian")
print(f"   Found {len(all_files)} files")

# Step 2: Get books
print("\n[2] Getting books...")
books = client.table("books").select("*").execute()
print(f"   Found {len(books.data)} books")

# Step 3: Match and update each book
print("\n[3] Updating books...")
updated = 0
failed = []

for book in books.data:
    book_id = book['id']
    local_path = book.get('pdf_path_ru') or book.get('pdf_path_uz') or ""
    
    if not local_path or 'supabase' in local_path.lower():
        continue
    
    # Extract filename
    filename = local_path.split('\\')[-1].lower() if '\\' in local_path else local_path.lower()
    
    # Try to find match
    matched_url = None
    for key, url in all_files.items():
        if filename in key or key in filename:
            matched_url = url
            break
    
    if matched_url:
        # Update both columns
        try:
            result = client.table("books").update({
                "pdf_path_uz": matched_url,
                "pdf_path_ru": matched_url
            }).eq("id", book_id).execute()
            
            if result.data:
                print(f"   Updated: Book {book_id}")
                updated += 1
            else:
                print(f"   No data returned: Book {book_id}")
        except Exception as e:
            print(f"   Error: Book {book_id} - {e}")
            failed.append(book_id)
    else:
        failed.append(book_id)
        print(f"   No match: Book {book_id} - {filename[:40]}")

print(f"\n[4] Summary:")
print(f"   Updated: {updated}")
print(f"   Failed/No match: {len(failed)}")

# Verify
print("\n[5] Verification:")
verify = client.table("books").select("id, pdf_path_uz, pdf_path_ru").limit(5).execute()
for b in verify.data:
    uz = b.get('pdf_path_uz') or "None"
    status = "SUPABASE" if 'supabase' in uz.lower() else "LOCAL" if '\\' in uz else "NONE"
    print(f"   Book {b['id']}: {status} - {uz[:50]}...")
