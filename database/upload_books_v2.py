"""
Simple Book Upload to Supabase Storage
Uploads PDF files directly with better error handling
"""
import os
import sys
import urllib.parse
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = "https://rhjsndgajlvnhbzwayhc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"

BOOKS_DIR = Path(__file__).parent.parent / "books"
BUCKET_NAME = "books"


def transliterate_russian(text):
    """Convert Russian text to Latin for file paths."""
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
    """Create a safe storage path (ASCII only)."""
    # Transliterate Russian characters
    safe = transliterate_russian(path_str)
    # Replace spaces with underscores
    safe = safe.replace(' ', '_')
    # Remove or replace problematic characters
    safe = ''.join(c if c.isalnum() or c in '._-/' else '_' for c in safe)
    # Remove multiple underscores
    while '__' in safe:
        safe = safe.replace('__', '_')
    return safe


def main():
    print("=" * 60)
    print("SignPaper - Upload Books to Supabase Storage")
    print("=" * 60)
    
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print(f"Books directory: {BOOKS_DIR}")
    
    if not BOOKS_DIR.exists():
        print("ERROR: books directory not found!")
        return
    
    # Find all PDFs
    pdf_files = list(BOOKS_DIR.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files")
    
    uploaded = 0
    errors = 0
    
    for pdf_path in pdf_files:
        relative = pdf_path.relative_to(BOOKS_DIR)
        storage_path = safe_storage_path(str(relative).replace("\\", "/"))
        
        file_size = pdf_path.stat().st_size / (1024 * 1024)  # MB
        print(f"  [{uploaded+1}/{len(pdf_files)}] {relative.name} ({file_size:.1f}MB)...", end=" ", flush=True)
        
        # Skip files larger than 50MB
        if file_size > 50:
            print("SKIP (>50MB)")
            errors += 1
            continue
        
        try:
            with open(pdf_path, 'rb') as f:
                file_data = f.read()
            
            # Try to upload
            result = client.storage.from_(BUCKET_NAME).upload(
                storage_path,
                file_data,
                file_options={"content-type": "application/pdf", "upsert": "true"}
            )
            
            # Get URL
            url = client.storage.from_(BUCKET_NAME).get_public_url(storage_path)
            print("OK")
            uploaded += 1
            
            # Update database with URL
            # Parse language, subject, grade from path
            parts = str(relative).replace("\\", "/").split("/")
            if len(parts) >= 3:
                lang = parts[0]  # uzbek or russian
                subject_folder = parts[1]
                
                # Determine subject
                subject_map = {
                    'matematika': 'matematika', 'Matematika': 'matematika',
                    'fizika': 'fizika', 'Fizika': 'fizika',
                    'kimyo': 'kimyo', 'Kimyo': 'kimyo',
                    'biologiya': 'biologiya', 'Biologiya': 'biologiya',
                    'tarix': 'tarix', 'Tarix': 'tarix',
                    'Математика': 'matematika',
                    'Физика': 'fizika',
                    'Химия': 'kimyo',
                    'Биология': 'biologiya',
                    'История': 'tarix',
                }
                subject = subject_map.get(subject_folder, 'other')
                
                # Extract grade from filename
                import re
                grade_match = re.search(r'(\d+)', pdf_path.stem)
                grade = int(grade_match.group(1)) if grade_match else 5
                if not (1 <= grade <= 11):
                    grade = 5
                
                # Check if book exists
                existing = client.table("books").select("id").eq("subject", subject).eq("grade", grade).execute()
                
                if existing.data:
                    book_id = existing.data[0]["id"]
                    # Update URL
                    field = "pdf_url_uz" if lang == "uzbek" else "pdf_url_ru"
                    client.table("books").update({field: url}).eq("id", book_id).execute()
                else:
                    # Create new book
                    title_uz = f"{subject.capitalize()} {grade}-sinf" if lang == "uzbek" else ""
                    title_ru = f"{subject.capitalize()} {grade} klass" if lang == "russian" else ""
                    
                    insert_data = {
                        "subject": subject,
                        "grade": grade,
                        "title_uz": title_uz or pdf_path.stem,
                        "title_ru": title_ru or pdf_path.stem,
                        "pdf_url_uz" if lang == "uzbek" else "pdf_url_ru": url
                    }
                    client.table("books").insert(insert_data).execute()
            
        except Exception as e:
            error_str = str(e)
            if "Duplicate" in error_str or "already exists" in error_str:
                print("EXISTS")
                uploaded += 1
            else:
                print(f"ERROR: {error_str[:50]}")
                errors += 1
    
    print("=" * 60)
    print(f"Done! Uploaded: {uploaded}, Errors: {errors}")
    
    # Show stats
    result = client.table("books").select("id", count="exact").execute()
    print(f"Total books in database: {result.count}")
    
    # Show storage contents
    result = client.storage.from_(BUCKET_NAME).list('')
    print(f"Storage folders: {[f.get('name') for f in result]}")


if __name__ == "__main__":
    main()
