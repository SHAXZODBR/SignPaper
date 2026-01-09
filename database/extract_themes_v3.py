"""
Complete Theme Extraction v3
Finds PDFs locally, matches to books, extracts themes with real names and content.
"""
import os
import sys
import re
from pathlib import Path

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

import fitz
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rhjsndgajlvnhbzwayhc.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
BOOKS_DIR = Path(__file__).parent.parent / "books"


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def get_subject_from_folder(folder_name: str) -> str:
    """Map folder name to subject code."""
    mapping = {
        'matematika': 'matematika', 'Matematika': 'matematika',
        'fizika': 'fizika', 'Fizika': 'fizika',
        'kimyo': 'kimyo', 'Kimyo': 'kimyo',
        'biologiya': 'biologiya', 'Biologiya': 'biologiya',
        'tarix': 'tarix', 'Tarix': 'tarix',
        'ona_tili': 'ona_tili', 'Ona_tili': 'ona_tili',
        'algebra': 'matematika', 'Algebra': 'matematika',
        'geometriya': 'matematika', 'Geometriya': 'matematika',
        'Математика': 'matematika',
        'Физика': 'fizika',
        'Химия': 'kimyo',
        'Биология': 'biologiya',
        'История': 'tarix',
        'Алгебра': 'matematika',
        'Геометрия': 'matematika',
    }
    return mapping.get(folder_name, 'other')


def extract_grade(filename: str) -> int:
    """Extract grade from filename."""
    match = re.search(r'(\d+)', filename)
    if match:
        grade = int(match.group(1))
        if 1 <= grade <= 11:
            return grade
    return 5


def find_chapter_title(doc, start_page: int) -> str:
    """Find a meaningful title from the start of a chapter."""
    if start_page >= doc.page_count:
        return None
    
    page = doc[start_page]
    text = page.get_text("text")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    for line in lines[:12]:
        if len(line) < 5 or len(line) > 100:
            continue
        if re.match(r'^[\d\s\.\-,]+$', line):
            continue
        
        # Chapter patterns
        if re.match(r'^\d+[\.\-]?\s+\w', line):
            return line[:80]
        if re.match(r'^§\s*\d+', line):
            return line[:80]
        if re.match(r'^\d+\s*-\s*bob', line, re.IGNORECASE):
            return line[:80]
        if re.match(r'^\d+\s*-\s*глава', line, re.IGNORECASE):
            return line[:80]
        
        # First text line with enough content
        if len(line) > 15 and line[0].isalpha():
            alpha = sum(c.isalpha() or c.isspace() for c in line) / len(line)
            if alpha > 0.65:
                return line[:80]
    
    return None


def extract_text_range(doc, start: int, end: int, max_chars: int = 5000) -> str:
    """Extract text from page range."""
    parts = []
    for p in range(start, min(end + 1, doc.page_count)):
        parts.append(doc[p].get_text("text"))
    text = "\n".join(parts)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text[:max_chars] if len(text) > max_chars else text


def main():
    print("=" * 60, flush=True)
    print("SignPaper - Theme Extraction v3", flush=True)
    print("=" * 60, flush=True)
    
    client = get_client()
    
    # Get all books from database
    books_result = client.table("books").select("*").execute()
    db_books = {(b['subject'], b['grade']): b for b in books_result.data}
    print(f"Books in database: {len(db_books)}", flush=True)
    
    # Find all PDFs
    pdf_files = list(BOOKS_DIR.rglob("*.pdf"))
    print(f"PDF files found: {len(pdf_files)}\n", flush=True)
    
    themes_added = 0
    errors = 0
    
    for pdf_path in pdf_files:
        relative = pdf_path.relative_to(BOOKS_DIR)
        parts = str(relative).replace("\\", "/").split("/")
        
        if len(parts) < 2:
            continue
        
        lang = parts[0]  # uzbek or russian
        subject_folder = parts[1] if len(parts) > 1 else ""
        subject = get_subject_from_folder(subject_folder)
        grade = extract_grade(pdf_path.stem)
        
        # Find matching book in database
        book_key = (subject, grade)
        if book_key not in db_books:
            print(f"  [SKIP] No book for {subject} grade {grade}: {pdf_path.name}", flush=True)
            continue
        
        book = db_books[book_key]
        book_id = book['id']
        
        # Check if themes already exist
        existing = client.table("themes").select("id", count="exact").eq("book_id", book_id).execute()
        if existing.count and existing.count > 0:
            print(f"  [SKIP] {pdf_path.name} - already has {existing.count} themes", flush=True)
            continue
        
        print(f"\n[{subject} {grade}] {pdf_path.name}", flush=True)
        
        is_uzbek = (lang == 'uzbek')
        
        try:
            doc = fitz.open(str(pdf_path))
            total_pages = doc.page_count
            print(f"  Pages: {total_pages}", flush=True)
            
            # Calculate chapter divisions
            if total_pages < 20:
                num_chapters = 3
            elif total_pages < 50:
                num_chapters = 5
            elif total_pages < 100:
                num_chapters = 8
            else:
                num_chapters = 10
            
            pages_per_chapter = total_pages // num_chapters
            
            for i in range(num_chapters):
                start = i * pages_per_chapter
                end = (i + 1) * pages_per_chapter - 1 if i < num_chapters - 1 else total_pages - 1
                
                # Find title
                title = find_chapter_title(doc, start)
                if not title:
                    title = f"{i + 1}-bo'lim (p.{start + 1}-{end + 1})"
                
                # Extract content
                content = extract_text_range(doc, start, end)
                
                if len(content) < 100:
                    continue
                
                # Insert theme
                theme_data = {
                    'book_id': book_id,
                    'order_index': i + 1,
                    'start_page': start,
                    'end_page': end,
                    'chapter_number': str(i + 1),
                }
                
                if is_uzbek:
                    theme_data['name_uz'] = title
                    theme_data['content_uz'] = content
                else:
                    theme_data['name_ru'] = title
                    theme_data['content_ru'] = content
                
                try:
                    client.table("themes").insert(theme_data).execute()
                    themes_added += 1
                    print(f"  + {title[:45]}... (p.{start + 1}-{end + 1})", flush=True)
                except Exception as e:
                    errors += 1
            
            doc.close()
            
        except Exception as e:
            print(f"  Error: {e}", flush=True)
            errors += 1
    
    print("\n" + "=" * 60, flush=True)
    print(f"Done! Added: {themes_added}, Errors: {errors}", flush=True)
    
    result = client.table("themes").select("id", count="exact").execute()
    print(f"Total themes: {result.count}", flush=True)


if __name__ == "__main__":
    main()
