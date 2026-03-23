import json
import os
import sys
import re
from typing import List, Dict, Any
from supabase import create_client, Client

# Supabase Credentials
SUPABASE_URL = "https://rhjsndgajlvnhbzwayhc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"

DATA_FILE = "/home/shakhzodbtr/Desktop/SignPaper/extracted_themes_v2.json"

def main():
    print("=" * 60)
    print("SignPaper - Refined Theme Sync")
    print("=" * 60)

    client = create_client(SUPABASE_URL, SUPABASE_KEY)

    print("Loading extracted themes...")
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        themes = json.load(f)
    print(f"Loaded {len(themes)} themes.")

    # 1. Fetch books and create better mapping
    print("Fetching books from database...")
    books_res = client.table("books").select("*").execute()
    sb_books = books_res.data
    print(f"Found {len(sb_books)} books in database.")

    book_map = {}
    for b in sb_books:
        bid = b['id']
        # Map by Titles
        if b.get('title_uz'): book_map[b['title_uz'].lower()] = bid
        if b.get('title_ru'): book_map[b['title_ru'].lower()] = bid
        # Map by Filenames in paths (Windows or Linux paths)
        if b.get('pdf_path_uz'): 
            fname = os.path.basename(b['pdf_path_uz'].replace('\\', '/')).lower()
            book_map[fname] = bid
        if b.get('pdf_path_ru'): 
            fname = os.path.basename(b['pdf_path_ru'].replace('\\', '/')).lower()
            book_map[fname] = bid

    # 2. Group Themes and Identify Missing Books
    grouped_themes = {}
    missing_book_filenames = set()

    for t in themes:
        filename = t['book'].lower()
        book_id = book_map.get(filename)
        
        if not book_id:
            # Try without .pdf
            book_id = book_map.get(filename.replace('.pdf', ''))
            
        if not book_id:
            missing_book_filenames.add(t['book'])
            continue
            
        if book_id not in grouped_themes:
            grouped_themes[book_id] = []
            
        grouped_themes[book_id].append({
            "book_id": book_id,
            "name_uz": t['title'] if t['lang'] == 'uz' else None,
            "name_ru": t['title'] if t['lang'] == 'ru' else None,
            "start_page": t['page'] - 1,
            "end_page": t['page'],
            "is_active": True
        })

    # 3. Create Missing Books
    if missing_book_filenames:
        print(f"Creating {len(missing_book_filenames)} missing book records...")
        for filename in missing_book_filenames:
            # Basic metadata extraction from filename
            lang = 'uz' if '_uzb' in filename.lower() or 'sinf' in filename.lower() else 'ru'
            grade_match = re.search(r'(\d+)', filename)
            grade = int(grade_match.group(1)) if grade_match else 5
            
            # Subject heuristic
            subject = 'other'
            for s in ['matematika', 'algebra', 'geometriya', 'fizika', 'kimyo', 'biologiya', 'tarix']:
                if s in filename.lower():
                    subject = s
                    break
            
            title = filename.replace('.pdf', '')
            insert_data = {
                "subject": subject,
                "grade": grade,
                "title_uz": title if lang == 'uz' else None,
                "title_ru": title if lang == 'ru' else None,
                "is_active": True,
                "pdf_path_uz": filename if lang == 'uz' else None,
                "pdf_path_ru": filename if lang == 'ru' else None
            }
            try:
                res = client.table("books").insert(insert_data).execute()
                if res.data:
                    new_id = res.data[0]['id']
                    book_map[filename.lower()] = new_id
                    # Add themes for this newly created book
                    grouped_themes[new_id] = [
                        {
                            "book_id": new_id,
                            "name_uz": t['title'] if t['lang'] == 'uz' else None,
                            "name_ru": t['title'] if t['lang'] == 'ru' else None,
                            "start_page": t['page'] - 1,
                            "end_page": t['page'],
                            "is_active": True
                        } for t in themes if t['book'] == filename
                    ]
            except Exception as e:
                print(f"Failed to create book {filename}: {e}")

    # 4. Bulk Insert Themes
    print(f"Starting bulk sync for {len(grouped_themes)} books...")
    total_synced = 0
    
    for book_id, book_themes in grouped_themes.items():
        # First, clear existing themes for this book to avoid duplicates in case of rerun
        # Commented out for now as it might be dangerous if not using a clean DB
        # client.table("themes").delete().eq("book_id", book_id).execute()
        
        print(f"  Syncing {len(book_themes)} themes for book {book_id}...", end=" ", flush=True)
        
        batch_size = 1000 # Increased batch size
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
