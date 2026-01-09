"""
Extract Real Theme Names from PDFs
Scans PDFs for chapter headings and updates theme names in Supabase.
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


def extract_chapter_title_from_page(doc, page_num):
    """
    Try to extract a chapter title from the first few lines of a page.
    Looks for patterns like chapter headers.
    """
    if page_num >= doc.page_count:
        return None
    
    page = doc[page_num]
    text = page.get_text("text")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    if not lines:
        return None
    
    # Look for potential chapter titles in first 5 lines
    for line in lines[:5]:
        # Skip very short or very long lines
        if len(line) < 3 or len(line) > 100:
            continue
        
        # Skip lines that are just numbers or page numbers
        if re.match(r'^\d+$', line):
            continue
        
        # Skip lines that look like headers with just numbers
        if re.match(r'^[\d\.\-\s]+$', line):
            continue
        
        # Check for chapter-like patterns
        chapter_patterns = [
            r'^(\d+[\.\-]\s*\d*[\.\-]?\s*.+)$',  # "1. Title" or "1.1. Title"
            r'^(bob|глава|chapter)\s*\d*[\.:]\s*(.+)$',  # "Bob 1: Title"
            r'^(§\s*\d+[\.\-]?\s*.+)$',  # § symbol
            r'^([IVX]+[\.\-]\s*.+)$',  # Roman numerals
            r'^(\d+\s+[\w\s]{5,})$',  # "1 Some Title Text"
        ]
        
        for pattern in chapter_patterns:
            match = re.match(pattern, line, re.IGNORECASE)
            if match:
                return line[:80]  # Return matched title, limit length
        
        # If first significant line is mostly text (not numbers), could be title
        if len(line) > 10 and not line[0].isdigit():
            alpha_ratio = sum(c.isalpha() for c in line) / len(line)
            if alpha_ratio > 0.6:
                return line[:80]
    
    return None


def main():
    print("=" * 60)
    print("SignPaper - Extract Real Theme Names")  
    print("=" * 60)
    
    client = get_client()
    
    # Get all themes with their books
    themes_result = client.table("themes").select(
        "id, book_id, name_uz, name_ru, start_page, end_page, books(subject, grade, pdf_path_uz, pdf_path_ru)"
    ).execute()
    
    themes = themes_result.data or []
    print(f"Found {len(themes)} themes to check\n")
    
    updated = 0
    errors = 0
    
    for theme in themes:
        theme_id = theme['id']
        name_uz = theme.get('name_uz') or ''
        name_ru = theme.get('name_ru') or ''
        start_page = theme.get('start_page') or 0
        book = theme.get('books', {})
        
        # Skip if already has real name (not "Bob N")
        if name_uz and not name_uz.startswith('Bob '):
            continue
        if name_ru and not name_ru.startswith('Bob '):
            continue
        
        # Get PDF path
        pdf_path_uz = book.get('pdf_path_uz')
        pdf_path_ru = book.get('pdf_path_ru')
        
        pdf_path = None
        is_uzbek = False
        
        if pdf_path_uz and Path(pdf_path_uz).exists():
            pdf_path = pdf_path_uz
            is_uzbek = True
        elif pdf_path_ru and Path(pdf_path_ru).exists():
            pdf_path = pdf_path_ru
            is_uzbek = False
        
        if not pdf_path:
            continue
        
        try:
            doc = fitz.open(pdf_path)
            new_title = extract_chapter_title_from_page(doc, start_page)
            doc.close()
            
            if new_title and new_title != name_uz and new_title != name_ru:
                # Update theme with real name
                update_data = {}
                if is_uzbek:
                    update_data['name_uz'] = new_title
                else:
                    update_data['name_ru'] = new_title
                
                client.table("themes").update(update_data).eq("id", theme_id).execute()
                
                print(f"  Theme {theme_id}: '{name_uz or name_ru}' -> '{new_title}'")
                updated += 1
                
        except Exception as e:
            print(f"  Error theme {theme_id}: {e}")
            errors += 1
    
    print("\n" + "=" * 60)
    print(f"Done! Updated: {updated}, Errors: {errors}")


if __name__ == "__main__":
    main()
