"""
Upload Books to Supabase Storage
Uploads all PDFs from books/ folder and updates the database.
"""
import os
import sys
import re
from pathlib import Path
from supabase import create_client
from dotenv import load_dotenv

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Use service_role key if available (for storage operations)
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY", SUPABASE_KEY)

BOOKS_DIR = Path(__file__).parent.parent / "books"
BUCKET_NAME = "books"


def get_client():
    """Get Supabase client."""
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


def create_storage_bucket(client):
    """Create books storage bucket if it doesn't exist."""
    try:
        # Try to create bucket
        client.storage.create_bucket(
            BUCKET_NAME,
            options={
                "public": True,
                "file_size_limit": 52428800  # 50MB
            }
        )
        print(f"✅ Created bucket: {BUCKET_NAME}")
    except Exception as e:
        if "already exists" in str(e).lower() or "duplicate" in str(e).lower():
            print(f"ℹ️ Bucket '{BUCKET_NAME}' already exists")
        else:
            print(f"⚠️ Bucket error: {e}")


def extract_info_from_filename(filepath: str, language: str):
    """
    Extract subject and grade from filename.
    Returns: (subject, grade, title)
    """
    filename = Path(filepath).stem  # Get filename without extension
    
    # Detect subject from parent folder
    parent = Path(filepath).parent.name.lower()
    
    subject_map = {
        'matematika': 'matematika', 'математика': 'matematika',
        'fizika': 'fizika', 'физика': 'fizika',
        'kimyo': 'kimyo', 'химия': 'kimyo',
        'biologiya': 'biologiya', 'биология': 'biologiya',
        'tarix': 'tarix', 'история': 'tarix',
        'geografiya': 'geografiya', 'география': 'geografiya',
        'informatika': 'informatika', 'информатика': 'informatika',
    }
    
    subject = 'other'
    for key, value in subject_map.items():
        if key in parent:
            subject = value
            break
    
    # Extract grade from filename
    grade_patterns = [
        r'(\d+)[-_\s]*(sinf|klass|класс|кл)',  # 5-sinf, 5 класс
        r'(sinf|klass|класс|кл)[-_\s]*(\d+)',  # sinf 5
        r'(\d+)[-_\s]*(sinf|class)',
        r'(\d{1,2})(?=\s|[-_]|$)',  # Just a number
    ]
    
    grade = 5  # Default
    for pattern in grade_patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            # Find the digit group
            for group in match.groups():
                if group and group.isdigit():
                    g = int(group)
                    if 1 <= g <= 11:
                        grade = g
                        break
            break
    
    return subject, grade, filename


def upload_pdf(client, local_path: str, storage_path: str):
    """Upload a PDF to Supabase Storage."""
    import urllib.parse
    
    try:
        with open(local_path, 'rb') as f:
            file_data = f.read()
        
        # URL-encode the storage path for Cyrillic characters
        # But keep forward slashes as path separators
        parts = storage_path.split('/')
        encoded_parts = [urllib.parse.quote(part, safe='') for part in parts]
        encoded_path = '/'.join(encoded_parts)
        
        # Upload to storage
        result = client.storage.from_(BUCKET_NAME).upload(
            encoded_path,
            file_data,
            file_options={"content-type": "application/pdf", "upsert": "true"}
        )
        
        # Get public URL
        public_url = client.storage.from_(BUCKET_NAME).get_public_url(encoded_path)
        return public_url
        
    except Exception as e:
        error_msg = str(e).lower()
        if "already exists" in error_msg or "duplicate" in error_msg:
            # Return existing URL
            parts = storage_path.split('/')
            encoded_parts = [urllib.parse.quote(part, safe='') for part in parts]
            encoded_path = '/'.join(encoded_parts)
            return client.storage.from_(BUCKET_NAME).get_public_url(encoded_path)
        elif "size" in error_msg or "limit" in error_msg or "too large" in error_msg:
            print(f"    [SIZE LIMIT] File too large, skipping", flush=True)
        else:
            print(f"    [ERROR] {e}", flush=True)
        return None


def get_or_create_book(client, subject: str, grade: int, title_uz: str, title_ru: str):
    """Get existing book or create new one."""
    try:
        # Check if book exists
        result = client.table("books").select("id").eq(
            "subject", subject
        ).eq("grade", grade).execute()
        
        if result.data:
            return result.data[0]["id"]
        
        # Create new book
        result = client.table("books").insert({
            "subject": subject,
            "grade": grade,
            "title_uz": title_uz,
            "title_ru": title_ru,
        }).execute()
        
        return result.data[0]["id"]
        
    except Exception as e:
        print(f"  ❌ Book error: {e}")
        return None


def update_book_pdf_url(client, book_id: int, url: str, language: str):
    """Update book with PDF URL."""
    try:
        field = "pdf_url_uz" if language == "uzbek" else "pdf_url_ru"
        client.table("books").update({field: url}).eq("id", book_id).execute()
    except Exception as e:
        print(f"  ❌ Update error: {e}")


def main():
    print("=" * 60, flush=True)
    print("SignPaper - Upload Books to Supabase", flush=True)
    print("=" * 60, flush=True)
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: SUPABASE_URL and SUPABASE_KEY must be set in .env", flush=True)
        return
    
    print(f"URL: {SUPABASE_URL}", flush=True)
    
    client = get_client()
    
    # Create storage bucket
    print("\nSetting up storage bucket...", flush=True)
    create_storage_bucket(client)
    
    # Find all PDFs
    print("\n🔍 Finding PDF files...")
    
    uploaded = 0
    errors = 0
    
    for language in ["uzbek", "russian"]:
        lang_dir = BOOKS_DIR / language
        if not lang_dir.exists():
            continue
        
        print(f"\n📁 Processing {language}...")
        
        for pdf_path in lang_dir.rglob("*.pdf"):
            relative_path = pdf_path.relative_to(BOOKS_DIR)
            storage_path = str(relative_path).replace("\\", "/")
            
            print(f"  📄 {pdf_path.name}...")
            
            # Extract info
            subject, grade, title = extract_info_from_filename(str(pdf_path), language)
            
            # Create title
            if language == "uzbek":
                title_uz = f"{subject.capitalize()} {grade}-sinf"
                title_ru = ""
            else:
                title_uz = ""
                title_ru = f"{subject.capitalize()} {grade} класс"
            
            # Get or create book
            book_id = get_or_create_book(client, subject, grade, title_uz, title_ru)
            
            if not book_id:
                errors += 1
                continue
            
            # Upload PDF
            url = upload_pdf(client, str(pdf_path), storage_path)
            
            if url:
                update_book_pdf_url(client, book_id, url, language)
                uploaded += 1
                print(f"    ✅ Uploaded -> Book #{book_id}")
            else:
                errors += 1
    
    print("\n" + "=" * 60)
    print(f"✅ Done! Uploaded: {uploaded}, Errors: {errors}")
    print("=" * 60)
    
    # Show book count
    result = client.table("books").select("id", count="exact").execute()
    print(f"📚 Total books in database: {result.count}")


if __name__ == "__main__":
    main()
