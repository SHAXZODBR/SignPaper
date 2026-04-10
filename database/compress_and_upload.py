import os
import sys
import subprocess
import re
from pathlib import Path
from supabase import create_client

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

SUPABASE_URL = "https://rhjsndgajlvnhbzwayhc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"

BOOKS_DIR = Path(__file__).parent.parent / "books"
BUCKET_NAME = "books"

def transliterate_russian(text):
    translit_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
        'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
        'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
        'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
        'Ф': 'F', 'Х': 'Kh', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
        'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
    }
    result = []
    for char in text:
        result.append(translit_map.get(char, char))
    return ''.join(result)

def safe_storage_path(path_str):
    safe = transliterate_russian(path_str)
    safe = safe.replace(' ', '_')
    safe = ''.join(c if c.isalnum() or c in '._-/' else '_' for c in safe)
    while '__' in safe:
        safe = safe.replace('__', '_')
    return safe

def compress_pdf(input_path, output_path):
    print(f"Compressing {input_path.name}...")
    cmd = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/screen", "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-sOutputFile={str(output_path)}", str(input_path)
    ]
    try:
        subprocess.run(cmd, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Ghostscript error: {e}")
        return False

def normalize_filename(filename):
    name = os.path.splitext(filename)[0]
    return re.sub(r'[\s_]+', '', name.lower())

def main():
    print("=" * 60)
    print("Compressing and Uploading Large Books (>50MB)")
    print("=" * 60)
    
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    if not BOOKS_DIR.exists():
        print("ERROR: books directory not found!")
        return
    
    # Get books from DB to map easily
    res = client.table('books').select('id, pdf_path_uz, pdf_path_ru, pdf_url_uz, pdf_url_ru').execute()
    db_books = res.data
    lookup = {} # normalized_filename -> b['id'], lang
    for b in db_books:
        if b.get('pdf_path_uz'):
            lookup[normalize_filename(os.path.basename(b['pdf_path_uz'].replace('\\', '/')))] = (b['id'], 'uz')
        if b.get('pdf_path_ru'):
            lookup[normalize_filename(os.path.basename(b['pdf_path_ru'].replace('\\', '/')))] = (b['id'], 'ru')
    
    pdf_files = list(BOOKS_DIR.rglob("*.pdf"))
    uploaded = 0
    errors = 0
    
    for pdf_path in pdf_files:
        file_size = pdf_path.stat().st_size / (1024 * 1024)
        if file_size <= 50:
            continue
            
        print(f"\nProcessing Large File: {pdf_path.name} ({file_size:.1f}MB)")
        
        norm_name = normalize_filename(pdf_path.name)
        book_info = lookup.get(norm_name)
        if not book_info:
            for k, v in lookup.items():
                if norm_name in k or k in norm_name:
                    book_info = v
                    break
        
        if not book_info:
            print(f"Warning: Could not find matching book record in DB for {pdf_path.name}")
            # Still upload it just in case
        
        # Compress
        temp_out = Path(f"/tmp/compressed_{pdf_path.name}")
        if not compress_pdf(pdf_path, temp_out):
            errors += 1
            continue
            
        new_size = temp_out.stat().st_size / (1024 * 1024)
        print(f"Compressed size: {new_size:.1f}MB")
        
        if new_size > 50:
            print("ERROR: Still >50MB after compression. Skipping.")
            errors += 1
            temp_out.unlink()
            continue
            
        # Upload
        relative = pdf_path.relative_to(BOOKS_DIR)
        original_storage_path = str(relative).replace("\\", "/")
        
        # We must mimic the folder structure used by the repair script: /books/[language]/[grade]/[filename] 
        # But wait, we can just save it where it belongs, e.g. /uz/...
        storage_path = safe_storage_path(original_storage_path)
        
        try:
            with open(temp_out, 'rb') as f:
                file_data = f.read()
            
            print("Uploading to Supabase...")
            client.storage.from_(BUCKET_NAME).upload(
                storage_path,
                file_data,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
            
            url = client.storage.from_(BUCKET_NAME).get_public_url(storage_path)
            print(f"Uploaded successfully! URL: {url}")
            uploaded += 1
            
            if book_info:
                book_id, lang = book_info
                col_name = f"pdf_url_{lang}"
                client.table('books').update({col_name: url}).eq("id", book_id).execute()
                print(f"Updated DB for Book ID {book_id}")
                
        except Exception as e:
            print(f"ERROR uploading: {e}")
            errors += 1
            
        finally:
            if temp_out.exists():
                temp_out.unlink()
                
    print("\n" + "=" * 60)
    print(f"Done! Uploaded: {uploaded}, Errors: {errors}")

if __name__ == "__main__":
    main()
