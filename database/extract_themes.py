"""
Extract Themes from PDFs
Reads PDF files and extracts chapters/themes to Supabase.
"""
import os
import sys
import re
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

import fitz  # PyMuPDF
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rhjsndgajlvnhbzwayhc.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

BOOKS_DIR = Path(__file__).parent.parent / "books"


def get_client():
    """Get Supabase client."""
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def extract_toc_from_pdf(pdf_path: str):
    """
    Extract table of contents from PDF.
    Returns list of (title, page_number) tuples.
    """
    try:
        doc = fitz.open(pdf_path)
        toc = doc.get_toc()  # Get table of contents
        
        if toc:
            # Format: [[level, title, page], ...]
            chapters = []
            for level, title, page in toc:
                if level <= 2:  # Only top 2 levels
                    chapters.append({
                        'title': title.strip(),
                        'start_page': page - 1,  # 0-indexed
                        'level': level
                    })
            
            # Calculate end pages
            for i, chapter in enumerate(chapters):
                if i + 1 < len(chapters):
                    chapter['end_page'] = chapters[i + 1]['start_page'] - 1
                else:
                    chapter['end_page'] = doc.page_count - 1
            
            doc.close()
            return chapters
        
        doc.close()
        return []
    except Exception as e:
        print(f"    Error extracting TOC: {e}")
        return []


def extract_text_from_pages(pdf_path: str, start_page: int, end_page: int, max_chars: int = 5000):
    """
    Extract text content from a page range.
    """
    try:
        doc = fitz.open(pdf_path)
        text_parts = []
        
        for page_num in range(start_page, min(end_page + 1, doc.page_count)):
            page = doc[page_num]
            text = page.get_text("text")
            text_parts.append(text)
        
        doc.close()
        
        full_text = "\n".join(text_parts)
        # Clean up the text
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)  # Remove excessive newlines
        full_text = full_text.strip()
        
        # Truncate if too long
        if len(full_text) > max_chars:
            full_text = full_text[:max_chars] + "..."
        
        return full_text
    except Exception as e:
        print(f"    Error extracting text: {e}")
        return ""


def auto_detect_chapters(pdf_path: str, num_chapters: int = 10):
    """
    If no TOC available, auto-detect chapters by splitting PDF evenly.
    """
    try:
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        doc.close()
        
        if total_pages < 20:
            return []  # Too short for meaningful chapters
        
        pages_per_chapter = total_pages // num_chapters
        chapters = []
        
        for i in range(num_chapters):
            start = i * pages_per_chapter
            end = (i + 1) * pages_per_chapter - 1 if i < num_chapters - 1 else total_pages - 1
            
            chapters.append({
                'title': f"Bob {i + 1}",  # "Chapter" in Uzbek
                'start_page': start,
                'end_page': end,
                'level': 1
            })
        
        return chapters
    except Exception as e:
        print(f"    Error auto-detecting chapters: {e}")
        return []


def get_subject_info(folder_name: str):
    """Get subject code from folder name."""
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
    return subject_map.get(folder_name, 'other')


def extract_grade(filename: str) -> int:
    """Extract grade number from filename."""
    match = re.search(r'(\d+)', filename)
    if match:
        grade = int(match.group(1))
        if 1 <= grade <= 11:
            return grade
    return 5


def main():
    print("=" * 60)
    print("SignPaper - Extract Themes from PDFs")
    print("=" * 60)
    
    client = get_client()
    
    # Get all books from database
    books_result = client.table("books").select("*").execute()
    books = {(b['subject'], b['grade']): b for b in books_result.data}
    
    print(f"Found {len(books)} books in database")
    
    if not books:
        print("No books in database. Run upload_books_v2.py first!")
        return
    
    # Find all PDF files
    pdf_files = list(BOOKS_DIR.rglob("*.pdf"))
    print(f"Found {len(pdf_files)} PDF files\n")
    
    themes_added = 0
    errors = 0
    
    for pdf_path in pdf_files:
        relative = pdf_path.relative_to(BOOKS_DIR)
        parts = str(relative).replace("\\", "/").split("/")
        
        if len(parts) < 2:
            continue
        
        lang = parts[0]  # uzbek or russian
        subject_folder = parts[1]
        subject = get_subject_info(subject_folder)
        grade = extract_grade(pdf_path.stem)
        
        # Find matching book
        book_key = (subject, grade)
        if book_key not in books:
            print(f"  [SKIP] No book found for {subject} grade {grade}")
            continue
        
        book = books[book_key]
        book_id = book['id']
        
        print(f"\n[{subject} {grade}] {pdf_path.name}")
        
        # Check if themes already exist for this book
        existing = client.table("themes").select("id", count="exact").eq("book_id", book_id).execute()
        if existing.count and existing.count > 0:
            print(f"  Already has {existing.count} themes, skipping")
            continue
        
        # Extract chapters
        chapters = extract_toc_from_pdf(str(pdf_path))
        
        if not chapters:
            print("  No TOC found, auto-detecting chapters...")
            chapters = auto_detect_chapters(str(pdf_path))
        
        if not chapters:
            print("  Could not extract chapters, skipping")
            errors += 1
            continue
        
        print(f"  Found {len(chapters)} chapters")
        
        # Add themes to database
        for i, chapter in enumerate(chapters[:15]):  # Limit to 15 chapters
            # Extract text content
            content = extract_text_from_pages(
                str(pdf_path), 
                chapter['start_page'], 
                chapter['end_page']
            )
            
            if len(content) < 50:
                continue  # Skip chapters with not enough content
            
            # Prepare theme data
            theme_data = {
                'book_id': book_id,
                'order_index': i + 1,
                'start_page': chapter['start_page'],
                'end_page': chapter['end_page'],
                'chapter_number': str(i + 1),
            }
            
            # Set name and content based on language
            if lang == 'uzbek':
                theme_data['name_uz'] = chapter['title']
                theme_data['content_uz'] = content
            else:
                theme_data['name_ru'] = chapter['title']
                theme_data['content_ru'] = content
            
            try:
                client.table("themes").insert(theme_data).execute()
                themes_added += 1
                print(f"    + {chapter['title'][:40]}...")
            except Exception as e:
                print(f"    Error: {e}")
                errors += 1
    
    print("\n" + "=" * 60)
    print(f"Done! Themes added: {themes_added}, Errors: {errors}")
    
    # Show stats
    result = client.table("themes").select("id", count="exact").execute()
    print(f"Total themes in database: {result.count}")


if __name__ == "__main__":
    main()
