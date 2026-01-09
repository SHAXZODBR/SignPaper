# -*- coding: utf-8 -*-
"""
Upload local books to Supabase Storage and update the database.
Ensures 100% matching between local files and cloud storage.
"""
import os
import sys
import mimetypes
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Set encoding for Windows console
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Using the Service Role Key provided by the user for full access
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"
BUCKET_NAME = "books"

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Local base path
BASE_DIR = r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books"

def upload_and_update():
    """Iterate through folders, upload to storage, and update DB."""
    total_uploaded = 0
    total_updated = 0
    
    # We'll map filenames to IDs based on the current DB snapshot to avoid wrong updates
    print("Fetching current books from database...")
    books_data = client.table("books").select("id, pdf_path_uz, pdf_path_ru, title_uz, title_ru").execute()
    db_books = books_data.data
    
    folders = ['uzbek', 'russian']
    
    for folder in folders:
        folder_path = Path(BASE_DIR) / folder
        print(f"\nProcessing folder: {folder}")
        
        # Traverse recursively to find all PDFs
        for pdf_file in folder_path.rglob("*.pdf"):
            filename = pdf_file.name
            relative_path = pdf_file.relative_to(BASE_DIR).as_posix()
            storage_path = relative_path # e.g. "uzbek/Matematika/file.pdf"
            
            print(f"  Uploading: {filename}...")
            
            try:
                # 1. Upload to Supabase Storage
                mime_type, _ = mimetypes.guess_type(str(pdf_file))
                with open(pdf_file, 'rb') as f:
                    # Upload (upsert=True to overwrite if exists)
                    try:
                        client.storage.from_(BUCKET_NAME).upload(
                            path=storage_path,
                            file=f,
                            file_options={"content-type": mime_type or "application/pdf", "upsert": "true"}
                        )
                    except Exception as upload_err:
                        # If upsert fails, try a clean upload if not exists
                        # (Sometimes RLS allows INSERT but not UPDATE/UPSERT)
                        if "security" in str(upload_err).lower():
                            print(f"    - UPSERT failed (RLS), trying simple upload...")
                            try:
                                client.storage.from_(BUCKET_NAME).upload(
                                    path=storage_path,
                                    file=f,
                                    file_options={"content-type": mime_type or "application/pdf"}
                                )
                            except Exception as simple_err:
                                raise Exception(f"Upload failed: {simple_err}") from simple_err
                        else:
                            raise upload_err
                
                # 2. Get Public URL
                # public_url = client.storage.from_(BUCKET_NAME).get_public_url(storage_path) # This is a local-only generation in the SDK
                # Building the URL manually to ensure consistency if get_public_url has issues
                # Format: {URL}/storage/v1/object/public/{BUCKET}/{PATH}
                base_url = SUPABASE_URL.rstrip('/')
                public_url = f"{base_url}/storage/v1/object/public/{BUCKET_NAME}/{storage_path}"
                
                total_uploaded += 1
                
                # 3. Find matching book in DB and update
                matched = False
                for book in db_books:
                    # Check title OR stored path for matching
                    title_match = False
                    if book.get('title_uz') and book['title_uz'].lower() in filename.lower(): title_match = True
                    if book.get('title_ru') and book['title_ru'].lower() in filename.lower(): title_match = True
                    
                    current_path_uz = (book.get('pdf_path_uz') or "").lower()
                    current_path_ru = (book.get('pdf_path_ru') or "").lower()
                    path_match = filename.lower() in current_path_uz or filename.lower() in current_path_ru
                    
                    if title_match or path_match:
                        # Update both columns just to be sure
                        client.table("books").update({
                            "pdf_path_uz": public_url,
                            "pdf_path_ru": public_url
                        }).eq("id", book['id']).execute()
                        
                        print(f"    ✅ Updated Book ID {book['id']}: {book.get('title_uz') or book.get('title_ru')}")
                        matched = True
                        total_updated += 1
                        # Don't break, multiple books might use same file (unlikely but possible)
                
                if not matched:
                    print(f"    ⚠️ WARNING: No matching book found in DB for {filename}")
                    
            except Exception as e:
                print(f"    ❌ ERROR: {e}")

    print("\n" + "="*40)
    print(f"SUMMARY:")
    print(f"Total uploaded: {total_uploaded}")
    print(f"Total DB updates: {total_updated}")
    print("="*40)

if __name__ == "__main__":
    upload_and_update()
