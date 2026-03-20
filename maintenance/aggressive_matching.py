# -*- coding: utf-8 -*-
"""
Aggressive fuzzy matching for missing books.
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
print("AGGRESSIVE MATCHING - 30 Missing Books")
print("=" * 60)

# Build file map
file_list = [] # List of (display_name, full_path, url)

def scan(path=""):
    try:
        items = client.storage.from_(BUCKET_NAME).list(path)
        for item in items:
            name = item.get('name', '')
            full_path = f"{path}/{name}" if path else name
            if item.get('id'):
                url = client.storage.from_(BUCKET_NAME).get_public_url(full_path)
                file_list.append({
                    'name': name.lower(),
                    'full_path': full_path.lower(),
                    'url': url
                })
            else:
                scan(full_path)
    except Exception as e:
        print(f"Error scanning {path}: {e}")

print("[1] Syncing storage...")
scan("uzbek")
scan("russian")
print(f"Found {len(file_list)} files in storage.")

# Get missing books
print("[2] Fetching missing books...")
books = client.table("books").select("*").execute()
missing = []
for b in books.data:
    uz = b.get('pdf_path_uz') or ""
    ru = b.get('pdf_path_ru') or ""
    if not ('supabase' in uz.lower() or 'supabase' in ru.lower()):
        missing.append(b)
print(f"Total missing: {len(missing)}")

# Aggressive matching
updated_count = 0

for b in missing:
    book_id = b['id']
    name = (b.get('title_uz') or b.get('title_ru') or b.get('subject') or "").lower()
    grade = str(b.get('grade')) if b.get('grade') else ""
    subject = (b.get('subject') or "").lower()
    
    match = None 
    
    # Strategy 1: Grade + Subject in filename
    for f in file_list:
        if grade in f['name'] and subject in f['name']:
            match = f['url']
            break
            
    # Strategy 2: Title keywords
    if not match:
        keywords = re.findall(r'\w+', name)
        for f in file_list:
            match_score = 0
            for kw in keywords:
                if len(kw) > 3 and kw in f['name']:
                    match_score += 1
            if match_score >= (len(keywords) // 2 + 1):
                match = f['url']
                break

    # Strategy 3: Grade + First character of subject (e.g. 'm' for math)
    if not match and grade and subject:
        for f in file_list:
            if grade in f['name'] and subject[0] in f['name']:
                # Extra check for common subjects
                subjects_uz = {'matematika': 'mat', 'fizika': 'fiz', 'kimyo': 'kim', 'biologiya': 'bio', 'tarix': 'tar'}
                if subject in subjects_uz and subjects_uz[subject] in f['name']:
                    match = f['url']
                    break

    if match:
        print(f"MATCH: Book {book_id} ('{name}') -> {match[:50]}...")
        client.table("books").update({
            "pdf_path_uz": match,
            "pdf_path_ru": match
        }).eq("id", book_id).execute()
        updated_count += 1
    else:
        print(f"FAIL:  Book {book_id} ('{name}') - No match found.")

print(f"\n[3] Done! Updated {updated_count} books.")
