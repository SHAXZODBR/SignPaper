import os
import sys
import re
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://rhjsndgajlvnhbzwayhc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"

def list_all_files(client, bucket, path=''):
    """Recursively list all files in a Supabase storage bucket."""
    all_files = []
    res = client.storage.from_(bucket).list(path)
    for item in res:
        if not item.get("id"):  # It's a folder
            folder_path = f"{path}/{item['name']}".strip('/')
            all_files.extend(list_all_files(client, bucket, folder_path))
        else:
            file_path = f"{path}/{item['name']}".strip('/')
            all_files.append({"name": item['name'], "path": file_path})
    return all_files

def normalize_filename(filename):
    """Normalize filename for comparison (remove extension, lower, remove spaces/underscores)."""
    name = os.path.splitext(filename)[0]
    return re.sub(r'[\s_]+', '', name.lower())

def main():
    print("=" * 60)
    print("Repairing PDF URLs in Supabase")
    print("=" * 60)
    
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Get all books
    print("Fetching all books from DB...")
    res = client.table('books').select('id, title_uz, title_ru, pdf_path_uz, pdf_path_ru, pdf_url_uz, pdf_url_ru').execute()
    books = res.data
    
    # Create lookup map
    lookup = {} # normalized_filename -> (book_id, lang_col_prefix)
    for b in books:
        if b.get('pdf_path_uz'):
            norm_name = normalize_filename(os.path.basename(b['pdf_path_uz'].replace('\\', '/')))
            lookup[norm_name] = (b['id'], 'uz')
        if b.get('pdf_path_ru'):
            norm_name = normalize_filename(os.path.basename(b['pdf_path_ru'].replace('\\', '/')))
            lookup[norm_name] = (b['id'], 'ru')
    
    print(f"Mapped {len(lookup)} unique local filenames to books.")
    
    # Get all files in storage
    print("Listing all files in storage bucket 'books'...")
    storage_files = list_all_files(client, 'books')
    print(f"Found {len(storage_files)} files in storage.")
    
    updates = 0
    not_found = []
    
    for f in storage_files:
        if not f['name'].endswith('.pdf'): continue
        
        url = client.storage.from_('books').get_public_url(f['path'])
        
        # We need to map this file to a book id based on filename
        # Wait, the filenames in storage have been safe_path'd (spaces to underscores, transliterated)
        # So we also need to transliterate local filenames to compare? No, safe_path preserves English exactly
        # But for russians? Actually `Matematika_5_-sinf_darslik.pdf` normalizes to `matematika5-sinfdarslik`
        norm_name = normalize_filename(f['name'])
        
        # Let's try to match it
        book_info = lookup.get(norm_name)
        
        # If not exact match, try partial match
        if not book_info:
            for k, v in lookup.items():
                if norm_name in k or k in norm_name:
                    book_info = v
                    break
                    
        if book_info:
            book_id, lang = book_info
            col_name = f"pdf_url_{lang}"
            
            # Update DB
            client.table('books').update({col_name: url}).eq("id", book_id).execute()
            print(f"✅ Mapped {f['name']} -> Book ID {book_id} ({col_name})")
            updates += 1
        else:
            not_found.append(f['name'])
            
    print("=" * 60)
    print(f"Done! Updated {updates}/{len(storage_files)} PDFs.")
    if not_found:
        print(f"Could not map {len(not_found)} files. Sample:")
        print(not_found[:10])
        
if __name__ == "__main__":
    main()
