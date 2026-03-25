import os
import re
from supabase import create_client

# Credentials found in repair_pdf_urls.py
URL = 'https://rhjsndgajlvnhbzwayhc.supabase.co'
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A'

client = create_client(URL, KEY)

def normalize_filename(filename):
    """Normalize filename for comparison (remove extension, lower, remove spaces/underscores/dots/dashes)."""
    name = os.path.splitext(filename)[0]
    # Remove all non-alphanumeric characters for robust matching
    return re.sub(r'[^a-zA-Z0-9]', '', name.lower())

def list_all_files(bucket, path=''):
    all_files = []
    try:
        res = client.storage.from_(bucket).list(path)
        for item in res:
            full_path = f"{path}/{item['name']}".strip('/')
            if not item.get("id"):  # folder
                all_files.extend(list_all_files(bucket, full_path))
            else:
                all_files.append({"name": item['name'], "path": full_path})
    except Exception as e:
        print(f"Error listing {path}: {e}")
    return all_files

def main():
    print("=" * 60)
    print("Syncing Supabase Storage -> Database")
    print("=" * 60)

    # 1. Fetch all files from storage
    print("Scanning storage bucket 'books'...")
    storage_files = list_all_files("books")
    
    # Map normalized filename to their public URL
    # We store multiple paths if they normalize to same name (just in case)
    storage_map = {}
    for f in storage_files:
        norm = normalize_filename(f['name'])
        if norm:
            url = client.storage.from_("books").get_public_url(f['path'])
            storage_map[norm] = url
            
    print(f"Indexed {len(storage_map)} unique filenames from storage.")

    # 2. Fetch all books from DB
    print("Fetching books from database...")
    res = client.table("books").select("*").execute()
    books = res.data or []
    print(f"Found {len(books)} books in 'books' table.")

    # 3. Update DB
    updates = 0
    matched_files = 0
    
    for book in books:
        update_data = {}
        for lang in ['uz', 'ru']:
            path_col = f'pdf_path_{lang}'
            url_col = f'pdf_url_{lang}'
            
            path_val = book.get(path_col)
            if path_val:
                # Extract filename from path (handle Windows \ and Linux /)
                filename = path_val.replace('\\', '/').split('/')[-1]
                norm_name = normalize_filename(filename)
                
                if norm_name in storage_map:
                    url = storage_map[norm_name]
                    # Only update if current URL is different or empty
                    if book.get(url_col) != url:
                        update_data[url_col] = url
                        matched_files += 1
        
        if update_data:
            try:
                client.table("books").update(update_data).eq("id", book['id']).execute()
                updates += 1
                print(f"✅ Updated Book ID {book['id']} ({book.get('title_uz') or book.get('title_ru')})")
            except Exception as e:
                print(f"❌ Error updating book {book['id']}: {e}")
    
    print("=" * 60)
    print(f"SUMMARY: Updated {updates} books, mapped {matched_files} PDF URLs.")
    print("End of Sync.")

if __name__ == "__main__":
    main()
