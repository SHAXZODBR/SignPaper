# -*- coding: utf-8 -*-
"""
Fix ALL 72 books with intelligent matching.
Uses fuzzy matching for mismatched filenames.
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
print("FIX ALL 72 BOOKS - Smart Matching")
print("=" * 60)

# Build complete file map
file_map = {}  # Multiple keys for each file

def normalize(name):
    """Normalize filename for matching."""
    name = name.lower()
    # Remove common variations
    name = re.sub(r'[_\-\s]+', '', name)
    name = re.sub(r'\.(pdf|PDF)$', '', name)
    # Remove numbers at start (like filename-123)
    name = re.sub(r'^filename[\-_]?\d+', '', name)
    return name

def scan_folder(path=""):
    """Scan folder recursively."""
    try:
        items = client.storage.from_(BUCKET_NAME).list(path)
        for item in items:
            name = item.get('name', '')
            full_path = f"{path}/{name}" if path else name
            
            if item.get('id'):  # File
                url = client.storage.from_(BUCKET_NAME).get_public_url(full_path)
                
                # Store with multiple keys for matching
                file_map[name.lower()] = url
                file_map[normalize(name)] = url
                file_map[full_path.lower()] = url
                
                # Also store by subject keywords
                keywords = ['matematika', 'fizika', 'kimyo', 'biologiya', 'tarix', 
                           'algebra', 'geometriya', 'informatika', 'ingliz', 'rus',
                           'ona_tili', 'adabiyot', 'история', 'математика', 'физика']
                for kw in keywords:
                    if kw in name.lower():
                        file_map[f"{kw}_{name.lower()}"] = url
            else:  # Folder
                scan_folder(full_path)
    except Exception as e:
        print(f"Error: {e}")

print("\n[1] Scanning Supabase Storage...")
scan_folder("uzbek")
scan_folder("russian")
print(f"   Found {len(file_map)} file keys")

# Get all books
print("\n[2] Getting books...")
books = client.table("books").select("*").execute()
print(f"   Found {len(books.data)} books")

# Smart matching
def find_match(local_path, language):
    """Find best match for local path."""
    if not local_path or 'supabase' in local_path.lower():
        return None  # Already updated or empty
    
    filename = local_path.split('\\')[-1].lower()
    norm_filename = normalize(filename)
    
    # Try exact match
    if filename in file_map:
        return file_map[filename]
    
    # Try normalized match
    if norm_filename in file_map:
        return file_map[norm_filename]
    
    # Try partial matching
    for key, url in file_map.items():
        # Check if language folder matches
        lang_folder = "uzbek" if language == "uz" else "russian"
        if lang_folder not in url.lower():
            continue
            
        # Check key similarity
        if norm_filename in key or key in norm_filename:
            return url
        
        # Check for grade match + subject
        grade_match = re.search(r'(\d+)', filename)
        if grade_match:
            grade = grade_match.group(1)
            if grade in key:
                # Also check subject keywords
                for kw in ['mat', 'fiz', 'kim', 'bio', 'tar', 'alg', 'geo', 'inf', 'ing', 'rus', 'ona', 'ada']:
                    if kw in filename and kw in key:
                        return url
    
    return None

# Update all books
print("\n[3] Updating books...")
updated = 0
still_missing = []

for book in books.data:
    book_id = book['id']
    title = book.get('title_uz', '') or book.get('title_ru', '') or f"Book {book_id}"
    pdf_uz = book.get('pdf_path_uz') or ""
    pdf_ru = book.get('pdf_path_ru') or ""
    
    update_data = {}
    
    # Try to match UZ
    if pdf_uz and 'supabase' not in pdf_uz.lower():
        match = find_match(pdf_uz, "uz")
        if match:
            update_data['pdf_path_uz'] = match
    
    # Try to match RU
    if pdf_ru and 'supabase' not in pdf_ru.lower():
        match = find_match(pdf_ru, "ru")
        if match:
            update_data['pdf_path_ru'] = match
    
    if update_data:
        try:
            client.table("books").update(update_data).eq("id", book_id).execute()
            updated += 1
            print(f"   OK: Book {book_id} - {title[:40]}")
        except Exception as e:
            print(f"   Error: {e}")
    else:
        # Check if already has valid URL or truly missing
        has_uz = pdf_uz and 'supabase' in pdf_uz.lower()
        has_ru = pdf_ru and 'supabase' in pdf_ru.lower()
        if not has_uz and not has_ru:
            still_missing.append((book_id, title[:40], pdf_uz.split('\\')[-1] if pdf_uz else "NO PATH"))

print(f"\n[4] Summary:")
print(f"   Updated: {updated} books")
print(f"   Still missing: {len(still_missing)} books")

if still_missing:
    print("\n   Missing books (need manual upload):")
    for bid, title, filename in still_missing[:10]:
        print(f"     Book {bid}: {title} ({filename})")
    if len(still_missing) > 10:
        print(f"     ... and {len(still_missing) - 10} more")

# Final verification
print("\n[5] Verification:")
sample = client.table("books").select("id, pdf_path_uz, pdf_path_ru").limit(10).execute()
ok_count = 0
for b in sample.data:
    uz = b.get('pdf_path_uz') or ""
    ru = b.get('pdf_path_ru') or ""
    has_url = 'supabase' in uz.lower() or 'supabase' in ru.lower()
    if has_url:
        ok_count += 1
        print(f"   Book {b['id']}: OK")
    else:
        print(f"   Book {b['id']}: MISSING")

print(f"\n   {ok_count}/10 sample books have Supabase URLs")
