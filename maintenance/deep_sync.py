# -*- coding: utf-8 -*-
"""
Intelligent sync: handles Cyrillic filenames and reports size limits.
"""
import os
import sys
import mimetypes
import re
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

# Set encoding for Windows console
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
# Use the known service role key for full access
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"
BUCKET_NAME = "books"

client = create_client(SUPABASE_URL, SUPABASE_KEY)
BASE_DIR = r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books"

def slugify(s):
    """Simple Latin slugifier for Cyrillic-ish filenames."""
    s = s.lower()
    # Simple mapping for common Cyrillic
    mapping = {
        'а':'a','б':'b','в':'v','г':'g','д':'d','е':'e','ё':'yo','ж':'zh','з':'z','и':'i','й':'j','к':'k','л':'l','м':'m','н':'n','о':'o','п':'p','р':'r','с':'s','т':'t','u':'u','ф':'f','х':'h','ц':'ts','ч':'ch','ш':'sh','щ':'sch','ъ':'','ы':'y','ь':'','э':'e','ю':'yu','я':'ya'
    }
    for k, v in mapping.items():
        s = s.replace(k, v)
    return re.sub(r'[^a-z0-9_.-]', '_', s)

def deep_sync():
    print("Fetching missing books...")
    books = client.table("books").select("*").execute().data
    
    missing = [b for b in books if not b.get('pdf_path_uz') or 'supabase' not in str(b.get('pdf_path_uz'))]
    print(f"Total missing: {len(missing)}")
    
    success_count = 0
    skipped_count = 0
    
    for b in missing:
        book_id = b['id']
        # Try to find file locally
        title = (b.get('title_uz') or b.get('title_ru') or b.get('subject') or "").lower()
        grade = str(b.get('grade'))
        
        found_file = None
        for folder in ['uzbek', 'russian']:
            folder_path = Path(BASE_DIR) / folder
            for pdf_file in folder_path.rglob("*.pdf"):
                if grade in pdf_file.name and any(kw in pdf_file.name.lower() for kw in title.split()):
                    found_file = pdf_file
                    break
            if found_file: break
            
        if not found_file:
            print(f"  [?] ID {book_id}: No local file match for '{title}' (Grade {grade})")
            continue
            
        # Check size (Supabase Free limit is 50MB)
        size_mb = found_file.stat().st_size / (1024 * 1024)
        if size_mb > 50:
            print(f"  [!] ID {book_id}: '{found_file.name}' is TOO LARGE ({size_mb:.1f}MB). Skipping.")
            skipped_count += 1
            continue
            
        # Target path with Latin characters
        safe_name = slugify(found_file.name)
        folder_prefix = 'uzbek' if 'uzbek' in str(found_file).lower() else 'russian'
        storage_path = f"{folder_prefix}/{safe_name}"
        
        print(f"  [+] ID {book_id}: Uploading '{found_file.name}' as '{storage_path}' ({size_mb:.1f}MB)...")
        
        try:
            with open(found_file, 'rb') as f:
                client.storage.from_(BUCKET_NAME).upload(
                    path=storage_path,
                    file=f,
                    file_options={"content-type": "application/pdf", "upsert": "true"}
                )
            
            base_url = SUPABASE_URL.rstrip('/')
            public_url = f"{base_url}/storage/v1/object/public/{BUCKET_NAME}/{storage_path}"
            
            client.table("books").update({
                "pdf_path_uz": public_url,
                "pdf_path_ru": public_url
            }).eq("id", book_id).execute()
            
            print(f"    - Updated ID {book_id} successfully.")
            success_count += 1
        except Exception as e:
            print(f"    - Error: {e}")

    print("\nDeep Sync complete!")
    print(f"Newly synced: {success_count}")
    print(skipped_count, "skipped due to 50MB limit.")

if __name__ == "__main__":
    deep_sync()
