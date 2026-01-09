"""
Complete Theme Extraction for SignPaper
Extracts proper themes from PDFs with:
- Real chapter names from PDF content
- Correct page ranges
- Full text content for search
"""
import os
import sys
import re
from pathlib import Path

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
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY required")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def find_chapter_title(doc, start_page: int) -> str:
    """
    Extract a meaningful chapter title from the first page of a chapter.
    Looks for headers, numbered sections, or prominent text.
    """
    if start_page >= doc.page_count:
        return None
    
    page = doc[start_page]
    text = page.get_text("text")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    if not lines:
        return None
    
    # Try to find a good title in first 10 lines
    for line in lines[:10]:
        # Skip very short or very long lines
        if len(line) < 5 or len(line) > 100:
            continue
        
        # Skip lines that are just numbers
        if re.match(r'^[\d\s\.\-]+$', line):
            continue
        
        # Good patterns for chapter titles
        patterns = [
            r'^(\d+[\.\-]?\s*.{5,})$',           # "1. Chapter Title" or "1 Chapter Title"
            r'^(§\s*\d+[\.\-]?\s*.{5,})$',       # § symbol
            r'^([IVX]+[\.\-]?\s*.{5,})$',        # Roman numerals
            r'^(\d+\s*-\s*bob[\.:]\s*.+)$',      # "1-bob: Title" (Uzbek)
            r'^(\d+\s*-\s*глава[\.:]\s*.+)$',   # "1-глава: Title" (Russian)
            r'^(bob\s*\d+[\.:]\s*.+)$',          # "Bob 1: Title"
            r'^(глава\s*\d+[\.:]\s*.+)$',        # "Глава 1: Title"
        ]
        
        for pattern in patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                title = match.group(1).strip()
                return title[:80]
        
        # If line starts with a letter and is mostly text, likely a title
        if line[0].isalpha() or line[0].isdigit():
            alpha_ratio = sum(c.isalpha() or c.isspace() for c in line) / len(line)
            if alpha_ratio > 0.7 and len(line) > 10:
                return line[:80]
    
    return None


def extract_text_from_range(doc, start_page: int, end_page: int, max_chars: int = 5000) -> str:
    """Extract text from a page range."""
    text_parts = []
    
    for page_num in range(start_page, min(end_page + 1, doc.page_count)):
        page = doc[page_num]
        text_parts.append(page.get_text("text"))
    
    full_text = "\n".join(text_parts)
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    full_text = full_text.strip()
    
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "..."
    
    return full_text


def create_chapters_from_pdf(doc, num_chapters: int = 8) -> list:
    """
    Create chapter divisions from a PDF.
    Splits PDF evenly and tries to find chapter titles at each division.
    """
    total_pages = doc.page_count
    
    if total_pages < 20:
        # Very short book - treat as single chapter
        return [{
            'start_page': 0,
            'end_page': total_pages - 1,
            'title': find_chapter_title(doc, 0) or "Asosiy matn"
        }]
    
    # Calculate pages per chapter
    pages_per_chapter = total_pages // num_chapters
    if pages_per_chapter < 10:
        num_chapters = max(1, total_pages // 15)
        pages_per_chapter = total_pages // num_chapters
    
    chapters = []
    for i in range(num_chapters):
        start = i * pages_per_chapter
        end = (i + 1) * pages_per_chapter - 1 if i < num_chapters - 1 else total_pages - 1
        
        # Find title at start of this section
        title = find_chapter_title(doc, start)
        if not title:
            title = f"{i + 1}-bob"  # "Chapter N" in Uzbek
        
        chapters.append({
            'start_page': start,
            'end_page': end,
            'title': title
        })
    
    return chapters


def main():
    print("=" * 60, flush=True)
    print("SignPaper - Complete Theme Extraction", flush=True)
    print("=" * 60, flush=True)
    
    client = get_client()
    
    # Get all books
    books_result = client.table("books").select("*").execute()
    books = books_result.data or []
    print(f"Found {len(books)} books in database\n", flush=True)
    
    themes_added = 0
    errors = 0
    
    for book in books:
        book_id = book['id']
        subject = book.get('subject', '')
        grade = book.get('grade', 0)
        title = book.get('title_uz') or book.get('title_ru') or f"{subject} {grade}"
        
        print(f"\n[{book_id}] {title}", flush=True)
        
        # Find PDF file
        pdf_path_uz = book.get('pdf_path_uz')
        pdf_path_ru = book.get('pdf_path_ru')
        
        pdf_path = None
        is_uzbek = True
        
        if pdf_path_uz and Path(pdf_path_uz).exists():
            pdf_path = pdf_path_uz
            is_uzbek = True
        elif pdf_path_ru and Path(pdf_path_ru).exists():
            pdf_path = pdf_path_ru
            is_uzbek = False
        
        if not pdf_path:
            print(f"  No PDF file found", flush=True)
            continue
        
        try:
            doc = fitz.open(pdf_path)
            print(f"  PDF: {doc.page_count} pages", flush=True)
            
            # Create chapters
            chapters = create_chapters_from_pdf(doc, num_chapters=8)
            
            for i, chapter in enumerate(chapters):
                start_page = chapter['start_page']
                end_page = chapter['end_page']
                title = chapter['title']
                
                # Extract content
                content = extract_text_from_range(doc, start_page, end_page)
                
                if len(content) < 50:
                    continue  # Skip empty chapters
                
                # Prepare theme data
                theme_data = {
                    'book_id': book_id,
                    'order_index': i + 1,
                    'start_page': start_page,
                    'end_page': end_page,
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
                    print(f"  + {title[:50]}... (p.{start_page}-{end_page})", flush=True)
                except Exception as e:
                    print(f"  Error inserting: {e}", flush=True)
                    errors += 1
            
            doc.close()
            
        except Exception as e:
            print(f"  Error: {e}", flush=True)
            errors += 1
    
    print("\n" + "=" * 60, flush=True)
    print(f"Done! Themes added: {themes_added}, Errors: {errors}", flush=True)
    
    # Verify
    result = client.table("themes").select("id", count="exact").execute()
    print(f"Total themes in database: {result.count}", flush=True)


if __name__ == "__main__":
    main()
