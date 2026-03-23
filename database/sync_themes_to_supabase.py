import json
import os
import sys
import re
from typing import List, Dict, Any
from supabase import create_client, Client

# Supabase Credentials (from upload_books_v2.py)
SUPABASE_URL = "https://rhjsndgajlvnhbzwayhc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"

DATA_FILE = "/home/shakhzodbtr/Desktop/SignPaper/extracted_themes_v2.json"

def main():
    print("=" * 60)
    print("SignPaper - Sync Themes to Supabase")
    print("=" * 60)

    if not os.path.exists(DATA_FILE):
        print(f"ERROR: Data file not found: {DATA_FILE}")
        return

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("Loading extracted themes...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        themes = json.load(f)
    print(f"Loaded {len(themes)} themes.")

    # 1. Map books to IDs
    print("Fetching books from database...")
    books_res = client.table("books").select("id, title_uz, title_ru, subject, grade").execute()
    existing_books = books_res.data
    print(f"Found {len(existing_books)} books in database.")

    # Create mapping: title -> id
    book_map = {}
    for b in existing_books:
        # Map by both languages since theme data might use either
        if b.get('title_uz'): book_map[b['title_uz'].lower()] = b['id']
        if b.get('title_ru'): book_map[b['title_ru'].lower()] = b['id']

    # 2. Process and Group Themes by Book
    grouped_themes = {}
    missing_books = set()

    for t in themes:
        book_title = t['book'].replace('.pdf', '')
        book_id = book_map.get(book_title.lower())
        
        if not book_id:
            # Try fuzzy match or just log missing
            missing_books.add(book_title)
            continue
            
        if book_id not in grouped_themes:
            grouped_themes[book_id] = []
            
        # Prepare theme data
        theme_data = {
            "book_id": book_id,
            "name_uz": t['title'] if t['lang'] == 'uz' else None,
            "name_ru": t['title'] if t['lang'] == 'ru' else None,
            "start_page": t['page'] - 1, # 0-indexed in DB usually
            "end_page": t['page'], # Approximation
            "is_active": True
        }
        grouped_themes[book_id].append(theme_data)

    if missing_books:
        print(f"WARNING: {len(missing_books)} books from extraction not found in database.")
        print(f"Sample missing: {list(missing_books)[:5]}")

    # 3. Bulk Insert Themes
    print(f"Starting sync for {len(grouped_themes)} books...")
    total_synced = 0
    
    # Supabase allows large batches but we'll do per-book or chunked for safety
    for book_id, book_themes in grouped_themes.items():
        print(f"  Syncing {len(book_themes)} themes for book ID {book_id}...", end=" ", flush=True)
        
        # Split into batches of 500
        batch_size = 500
        for i in range(0, len(book_themes), batch_size):
            batch = book_themes[i : i + batch_size]
            try:
                client.table("themes").insert(batch).execute()
                total_synced += len(batch)
            except Exception as e:
                print(f"\nERROR in batch {i}: {e}")
        
        print("Done")

    print("=" * 60)
    print(f"Sync complete! Total themes uploaded: {total_synced}")
    print("=" * 60)

if __name__ == "__main__":
    main()
