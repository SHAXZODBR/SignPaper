"""
SignPaper Database Rebuild v5
SCANS EVERY PAGE to find real chapter headers.
Extracts actual chapter names like "1. Natural sonlar".
"""
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple, Optional

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

import fitz  # PyMuPDF
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
PDF_DIR = Path(r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books")

# Subject detection patterns
SUBJECT_PATTERNS = {
    'biologiya': ['biolog', 'botanik', 'zoolog', 'биолог', 'ботаник', 'зоолог'],
    'fizika': ['fizik', 'физик'],
    'kimyo': ['kimyo', 'химия', 'химий'],
    'matematika': ['matemat', 'algebra', 'geometr', 'математ', 'алгебр', 'геометр'],
    'tarix': ['tarix', 'istori', 'истори'],
}

# Chapter header patterns - these indicate a chapter/theme start
CHAPTER_PATTERNS = [
    (r'^(\d+)\s*[\.\-\)]\s*(.+)', 'number'),      # "1. Natural sonlar" or "1) Topic"
    (r'^§\s*(\d+)[\.\s]*(.+)?', 'section'),        # "§ 1. Topic" or "§1 Topic"
    (r'^(\d+)\s*-?\s*(bob|глава|chapter)', 'bob'), # "1-bob", "1 глава"
    (r'^(bob|глава)\s*(\d+)', 'bob2'),             # "Bob 1", "Глава 1"
    (r'^(\d+)\s*-?\s*(mavzu|тема|dars|урок)', 'mavzu'), # "1-mavzu", "1 тема"
    (r'^([IVX]+)\s*[\.\-\)]\s*(.+)', 'roman'),     # "I. Topic", "II. Topic"
]


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def detect_subject(folder_name: str, filename: str) -> str:
    text = (folder_name + " " + filename).lower()
    for subject, patterns in SUBJECT_PATTERNS.items():
        for pattern in patterns:
            if pattern in text:
                return subject
    return 'other'


def extract_grade(filename: str) -> int:
    patterns = [
        r'(\d+)\s*-?\s*sinf',
        r'(\d+)\s*-?\s*класс',
        r'_(\d+)_',
    ]
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            grade = int(match.group(1))
            if 1 <= grade <= 11:
                return grade
    return 5


def get_text_with_font_info(page) -> List[Tuple[str, float, float]]:
    """Get text blocks with font size and y-position."""
    blocks = []
    try:
        text_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        for block in text_dict.get("blocks", []):
            if block.get("type") == 0:
                for line in block.get("lines", []):
                    line_text = ""
                    max_size = 0
                    for span in line.get("spans", []):
                        line_text += span.get("text", "")
                        max_size = max(max_size, span.get("size", 0))
                    
                    line_text = line_text.strip()
                    if line_text and max_size > 0:
                        y_pos = line.get("bbox", [0, 0, 0, 0])[1]
                        blocks.append((line_text, max_size, y_pos))
    except:
        pass
    return blocks


def is_chapter_header(text: str, font_size: float, avg_size: float) -> Tuple[bool, str]:
    """
    Check if text is a chapter header.
    Returns (is_header, cleaned_title).
    """
    text = text.strip()
    
    # Skip too short or too long
    if len(text) < 3 or len(text) > 120:
        return False, ""
    
    # Skip lines that are mostly numbers/punctuation
    alpha_count = sum(1 for c in text if c.isalpha())
    if alpha_count < 3:
        return False, ""
    
    # Check font size - headers are usually larger
    is_large_font = font_size >= avg_size * 1.15
    
    # Check patterns
    for pattern, ptype in CHAPTER_PATTERNS:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            # Only accept if font is larger than average OR it's a clear chapter pattern
            if is_large_font or ptype in ['bob', 'bob2', 'section', 'mavzu']:
                return True, text
    
    # Large font + short text + starts with capital = likely header
    if is_large_font and len(text) < 80:
        if text[0].isupper() and alpha_count / max(len(text), 1) > 0.6:
            # Make sure it's not a page number or garbage
            if not text.isdigit() and not re.match(r'^[\d\s\-\.]+$', text):
                return True, text
    
    return False, ""


def extract_chapters_from_book(doc) -> List[Dict]:
    """
    Scan every page and extract chapter headers.
    Returns list of chapters with name and page range.
    """
    chapters = []
    total_pages = doc.page_count
    
    # First pass: calculate average font size
    all_sizes = []
    for page_num in range(min(30, total_pages)):
        page = doc[page_num]
        blocks = get_text_with_font_info(page)
        for text, size, y in blocks:
            if len(text) > 10:
                all_sizes.append(size)
    
    avg_size = sum(all_sizes) / max(len(all_sizes), 1) if all_sizes else 12
    
    # Second pass: find chapter headers
    last_chapter_page = -5  # Avoid too many headers on same page
    
    for page_num in range(total_pages):
        page = doc[page_num]
        blocks = get_text_with_font_info(page)
        
        # Sort by y-position (top to bottom)
        blocks.sort(key=lambda x: x[2])
        
        for text, font_size, y_pos in blocks[:10]:  # Only check top 10 lines per page
            # Skip if we already found a chapter on recent pages
            if page_num - last_chapter_page < 2 and chapters:
                continue
                
            is_header, title = is_chapter_header(text, font_size, avg_size)
            
            if is_header:
                # Avoid duplicates
                if chapters and chapters[-1]['title'].lower() == title.lower():
                    continue
                
                chapters.append({
                    'title': title[:100],
                    'page': page_num,
                    'font_size': font_size
                })
                last_chapter_page = page_num
                break  # Only one chapter header per page
    
    # Calculate end pages
    for i, chapter in enumerate(chapters):
        if i + 1 < len(chapters):
            chapter['end_page'] = chapters[i + 1]['page'] - 1
        else:
            chapter['end_page'] = total_pages - 1
    
    return chapters


def extract_book_title(doc) -> str:
    """Extract book title from first pages."""
    for page_num in range(min(3, doc.page_count)):
        page = doc[page_num]
        blocks = get_text_with_font_info(page)
        
        # Find largest text
        best_title = None
        best_size = 0
        
        for text, size, y_pos in blocks:
            if len(text) > 5 and len(text) < 80 and size > best_size:
                alpha_ratio = sum(c.isalpha() or c.isspace() for c in text) / max(len(text), 1)
                if alpha_ratio > 0.5:
                    best_title = text
                    best_size = size
        
        if best_title and best_size > 14:
            return best_title[:80]
    
    return None


def extract_content(doc, start_page: int, end_page: int, max_chars: int = 6000) -> str:
    """Extract text content from page range."""
    parts = []
    for p in range(start_page, min(end_page + 1, doc.page_count)):
        parts.append(doc[p].get_text("text"))
    text = "\n".join(parts)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text[:max_chars]


def main():
    print("=" * 60)
    print("SignPaper - Database Rebuild v5")
    print("SCANS EVERY PAGE for real chapter headers")
    print("=" * 60)
    
    client = get_client()
    
    # Clear existing data
    print("\n[1] Clearing existing data...")
    try:
        client.table("themes").delete().neq("id", 0).execute()
        client.table("books").delete().neq("id", 0).execute()
        print("   Done")
    except Exception as e:
        print(f"   Warning: {e}")
    
    # Find PDFs
    print("\n[2] Finding PDFs...")
    pdf_files = list(PDF_DIR.rglob("*.pdf"))
    print(f"   Found {len(pdf_files)} PDF files")
    
    # Process each PDF
    print("\n[3] Processing books (scanning every page)...")
    books_created = 0
    themes_created = 0
    
    for pdf_path in sorted(pdf_files):
        relative = pdf_path.relative_to(PDF_DIR)
        parts = str(relative).replace("\\", "/").split("/")
        
        if len(parts) < 2:
            continue
        
        lang_folder = parts[0].lower()
        subject_folder = parts[1] if len(parts) > 1 else ""
        
        is_uzbek = (lang_folder == 'uzbek')
        language = 'uz' if is_uzbek else 'ru'
        
        subject = detect_subject(subject_folder, pdf_path.stem)
        grade = extract_grade(pdf_path.stem)
        
        print(f"\n   [{language.upper()}] {pdf_path.stem[:50]}")
        
        try:
            doc = fitz.open(str(pdf_path))
            print(f"      Pages: {doc.page_count}")
            
            # Extract book title
            book_title = extract_book_title(doc) or pdf_path.stem[:50]
            
            # Create book
            book_data = {
                'subject': subject,
                'grade': grade,
                'title_uz': book_title if is_uzbek else None,
                'title_ru': book_title if not is_uzbek else None,
                'pdf_path_uz': str(pdf_path) if is_uzbek else None,
                'pdf_path_ru': str(pdf_path) if not is_uzbek else None,
                'is_active': True,
            }
            
            result = client.table("books").insert(book_data).execute()
            book_id = result.data[0]['id']
            books_created += 1
            
            # Extract chapters by scanning every page
            chapters = extract_chapters_from_book(doc)
            print(f"      Found {len(chapters)} chapters")
            
            # Show first 3 chapter names as sample
            for ch in chapters[:3]:
                print(f"         - {ch['title'][:60]}")
            
            # Save themes
            for i, chapter in enumerate(chapters):
                content = extract_content(doc, chapter['page'], chapter['end_page'])
                
                if len(content) < 30:
                    continue
                
                theme_data = {
                    'book_id': book_id,
                    'order_index': i + 1,
                    'start_page': chapter['page'],
                    'end_page': chapter['end_page'],
                    'chapter_number': str(i + 1),
                    'is_active': True,
                }
                
                if is_uzbek:
                    theme_data['name_uz'] = chapter['title']
                    theme_data['content_uz'] = content
                else:
                    theme_data['name_ru'] = chapter['title']
                    theme_data['content_ru'] = content
                
                try:
                    client.table("themes").insert(theme_data).execute()
                    themes_created += 1
                except:
                    pass
            
            doc.close()
            
        except Exception as e:
            print(f"      Error: {e}")
    
    # Stats
    print("\n" + "=" * 60)
    print("[4] Final Statistics:")
    
    books_count = client.table("books").select("id", count="exact").execute()
    themes_count = client.table("themes").select("id", count="exact").execute()
    
    print(f"   📚 Books: {books_count.count}")
    print(f"   📑 Themes: {themes_count.count}")
    
    # Show sample themes
    print("\n[5] Sample theme names:")
    sample = client.table("themes").select("name_uz, name_ru").limit(15).execute()
    for t in sample.data:
        name = t.get('name_uz') or t.get('name_ru') or 'No name'
        print(f"   - {name[:70]}")
    
    print("\n✅ Rebuild complete!")


if __name__ == "__main__":
    main()
