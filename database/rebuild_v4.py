"""
SignPaper Complete Database Rebuild v4
IMPROVED: Extracts REAL chapter names using font size analysis and pattern matching.
"""
import os
import sys
import re
from pathlib import Path
from typing import List, Dict, Tuple

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

import fitz
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rhjsndgajlvnhbzwayhc.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
PDF_DIR = Path(r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books")

# Subject detection
SUBJECT_PATTERNS = {
    'biologiya': ['biolog', 'botanik', 'zoolog', 'биолог', 'ботаник', 'зоолог'],
    'fizika': ['fizik', 'физик'],
    'kimyo': ['kimyo', 'химия', 'химий'],
    'matematika': ['matemat', 'algebra', 'geometr', 'математ', 'алгебр', 'геометр'],
    'tarix': ['tarix', 'istori', 'истори'],
    'ona_tili': ['ona tili', 'adabiyot', 'родной', 'литератур'],
    'ingliz_tili': ['english', 'ingliz', 'английс'],
}

# Chapter heading patterns (more comprehensive)
CHAPTER_PATTERNS = [
    r'^(\d+)[\.\-\s]+(.+)',           # "1. Natural sonlar", "1-bob. ..."
    r'^§\s*(\d+)[\.\-\s]*(.+)?',      # "§ 1. ..."
    r'^([IVX]+)[\.\-\s]+(.+)',        # "I. ...", "II. ..."
    r'^(\d+)-?(bob|глава|chapter)',   # "1-bob", "1 глава"
    r'^(mavzu|тема)\s*(\d+)',         # "Mavzu 1", "Тема 1"
    r'^(\d+)-?(dars|урок)',           # "1-dars", "1 урок"
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
        r'(\d+)\s*-?\s*кл',
        r'_(\d+)_',
        r'\s(\d+)\s',
    ]
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            grade = int(match.group(1))
            if 1 <= grade <= 11:
                return grade
    return 5


def get_text_with_sizes(page) -> List[Tuple[str, float, int]]:
    """Extract text blocks with their font sizes and positions."""
    blocks = []
    text_dict = page.get_text("dict")
    
    for block in text_dict.get("blocks", []):
        if block.get("type") == 0:  # Text block
            for line in block.get("lines", []):
                text = ""
                max_size = 0
                for span in line.get("spans", []):
                    text += span.get("text", "")
                    max_size = max(max_size, span.get("size", 0))
                
                text = text.strip()
                if text and max_size > 0:
                    y_pos = line.get("bbox", [0, 0, 0, 0])[1]  # Top y position
                    blocks.append((text, max_size, y_pos))
    
    return blocks


def find_chapter_heading(text: str) -> Tuple[bool, str]:
    """Check if text is a chapter heading and extract title."""
    text = text.strip()
    
    # Skip very short or very long lines
    if len(text) < 3 or len(text) > 150:
        return False, ""
    
    # Skip lines that are mostly numbers/punctuation
    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
    if alpha_ratio < 0.4:
        return False, ""
    
    # Check chapter patterns
    for pattern in CHAPTER_PATTERNS:
        match = re.match(pattern, text, re.IGNORECASE)
        if match:
            return True, text
    
    # Check for keywords
    keywords = ['bob', 'глава', 'mavzu', 'тема', 'chapter', 'dars', 'урок']
    text_lower = text.lower()
    for kw in keywords:
        if kw in text_lower:
            return True, text
    
    return False, ""


def extract_themes_improved(doc, filename: str) -> List[Dict]:
    """
    Extract themes using improved algorithm:
    1. First try PDF TOC
    2. Then analyze font sizes to find headings
    3. Use pattern matching on large-font text
    """
    themes = []
    total_pages = doc.page_count
    
    # Method 1: Use PDF Table of Contents
    toc = doc.get_toc()
    if toc and len(toc) >= 3:
        print(f"      Using TOC ({len(toc)} entries)", flush=True)
        for level, title, page_num in toc:
            if level <= 2:
                themes.append({
                    'title': title.strip()[:100],
                    'page': max(0, page_num - 1),
                    'source': 'toc'
                })
        if themes:
            # Calculate end pages
            for i, theme in enumerate(themes):
                if i + 1 < len(themes):
                    theme['end_page'] = themes[i + 1]['page'] - 1
                else:
                    theme['end_page'] = total_pages - 1
            return themes
    
    # Method 2: Analyze font sizes to find headings
    print(f"      Analyzing font sizes...", flush=True)
    
    # First pass: discover font size distribution
    all_sizes = []
    for page_num in range(min(total_pages, 30)):  # Sample first 30 pages
        page = doc[page_num]
        blocks = get_text_with_sizes(page)
        for text, size, y in blocks:
            if len(text) > 10:
                all_sizes.append(size)
    
    if not all_sizes:
        all_sizes = [12]  # Default
    
    # Find "heading size" - larger than average
    avg_size = sum(all_sizes) / len(all_sizes)
    heading_threshold = avg_size * 1.15  # 15% larger than average
    
    # Second pass: find headings
    prev_page = -5
    for page_num in range(total_pages):
        page = doc[page_num]
        blocks = get_text_with_sizes(page)
        
        for text, size, y_pos in blocks:
            # Skip if too close to previous heading
            if page_num - prev_page < 3 and len(themes) > 0:
                continue
            
            # Check if this could be a heading
            is_heading = False
            clean_title = text
            
            # Large font = likely heading
            if size >= heading_threshold:
                is_chapter, title = find_chapter_heading(text)
                if is_chapter:
                    is_heading = True
                    clean_title = title
            
            # Check pattern even for smaller fonts (for chapter markers)
            if not is_heading:
                is_chapter, title = find_chapter_heading(text)
                if is_chapter and size >= avg_size:
                    is_heading = True
                    clean_title = title
            
            if is_heading:
                # Avoid duplicates
                if themes and themes[-1]['title'].lower() == clean_title.lower():
                    continue
                
                themes.append({
                    'title': clean_title[:100],
                    'page': page_num,
                    'source': 'font_analysis'
                })
                prev_page = page_num
                break  # Only one heading per page
    
    # Method 3: Fallback - divide by pages with content extraction
    if len(themes) < 3:
        print(f"      Using page division fallback", flush=True)
        themes = []
        
        if total_pages < 30:
            interval = max(5, total_pages // 4)
        elif total_pages < 80:
            interval = 12
        else:
            interval = 18
        
        for start_page in range(0, total_pages, interval):
            page = doc[start_page]
            blocks = get_text_with_sizes(page)
            
            # Find the largest-font text on page
            best_title = None
            best_size = 0
            
            for text, size, y_pos in blocks:
                if len(text) > 10 and len(text) < 80 and size > best_size:
                    alpha_ratio = sum(c.isalpha() for c in text) / max(len(text), 1)
                    if alpha_ratio > 0.5:
                        best_title = text
                        best_size = size
            
            if not best_title:
                best_title = f"{filename[:30]}_{len(themes) + 1}"
            
            themes.append({
                'title': best_title[:80],
                'page': start_page,
                'source': 'fallback'
            })
    
    # Calculate end pages
    for i, theme in enumerate(themes):
        if i + 1 < len(themes):
            theme['end_page'] = themes[i + 1]['page'] - 1
        else:
            theme['end_page'] = total_pages - 1
    
    return themes


def extract_content(doc, start_page: int, end_page: int, max_chars: int = 8000) -> str:
    """Extract text content from page range."""
    parts = []
    for p in range(start_page, min(end_page + 1, doc.page_count)):
        parts.append(doc[p].get_text("text"))
    text = "\n".join(parts)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text[:max_chars]


def extract_book_title(doc, filename: str) -> str:
    """Try to extract book title from first pages."""
    # Try first 3 pages
    for page_num in range(min(3, doc.page_count)):
        page = doc[page_num]
        blocks = get_text_with_sizes(page)
        
        # Find largest text that looks like a title
        best_title = None
        best_size = 0
        
        for text, size, y_pos in blocks:
            if len(text) > 10 and len(text) < 100 and size > best_size:
                # Check it's mostly letters
                alpha_ratio = sum(c.isalpha() or c.isspace() for c in text) / max(len(text), 1)
                if alpha_ratio > 0.6:
                    best_title = text
                    best_size = size
        
        if best_title and best_size > 14:  # Likely title if big font
            return best_title[:100]
    
    # Fallback to cleaned filename
    return re.sub(r'[_\-]+', ' ', filename)[:100]


def main():
    print("=" * 60, flush=True)
    print("SignPaper - Complete Database Rebuild v4", flush=True)
    print("IMPROVED: Real chapter names via font analysis", flush=True)
    print("=" * 60, flush=True)
    
    client = get_client()
    
    # Step 1: Clear ALL existing data
    print("\n[1] Clearing existing data...", flush=True)
    try:
        client.table("themes").delete().neq("id", 0).execute()
        client.table("books").delete().neq("id", 0).execute()
        print("   Done", flush=True)
    except Exception as e:
        print(f"   Warning: {e}", flush=True)
    
    # Step 2: Find PDFs
    print("\n[2] Finding PDFs...", flush=True)
    pdf_files = list(PDF_DIR.rglob("*.pdf"))
    print(f"   Found {len(pdf_files)} PDF files", flush=True)
    
    # Step 3: Process each PDF
    print("\n[3] Processing books and extracting themes...", flush=True)
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
        
        print(f"\n   [{language.upper()}] {pdf_path.stem[:50]}", flush=True)
        
        try:
            doc = fitz.open(str(pdf_path))
            
            # Extract real title
            book_title = extract_book_title(doc, pdf_path.stem)
            
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
            print(f"      Book ID: {book_id}, Title: {book_title[:40]}", flush=True)
            
            # Extract themes with improved method
            themes = extract_themes_improved(doc, pdf_path.stem)
            print(f"      Found {len(themes)} themes", flush=True)
            
            for i, theme_info in enumerate(themes):
                start_page = theme_info['page']
                end_page = theme_info['end_page']
                title = theme_info['title']
                
                content = extract_content(doc, start_page, end_page)
                
                if len(content) < 50:
                    continue
                
                theme_data = {
                    'book_id': book_id,
                    'order_index': i + 1,
                    'start_page': start_page,
                    'end_page': end_page,
                    'chapter_number': str(i + 1),
                    'is_active': True,
                }
                
                if is_uzbek:
                    theme_data['name_uz'] = title
                    theme_data['content_uz'] = content
                else:
                    theme_data['name_ru'] = title
                    theme_data['content_ru'] = content
                
                try:
                    client.table("themes").insert(theme_data).execute()
                    themes_created += 1
                except Exception as e:
                    pass
            
            doc.close()
            
        except Exception as e:
            print(f"      Error: {e}", flush=True)
    
    # Step 4: Show sample themes
    print("\n" + "=" * 60, flush=True)
    print("[4] Sample themes extracted:", flush=True)
    
    sample = client.table("themes").select("name_uz, name_ru, start_page, end_page").limit(10).execute()
    for t in sample.data:
        name = t.get('name_uz') or t.get('name_ru') or 'No name'
        print(f"   - {name[:60]} (p.{t.get('start_page')}-{t.get('end_page')})", flush=True)
    
    # Stats
    print("\n" + "=" * 60, flush=True)
    print("[5] Final Statistics:", flush=True)
    books_count = client.table("books").select("id", count="exact").execute()
    themes_count = client.table("themes").select("id", count="exact").execute()
    
    print(f"   📚 Books: {books_count.count}", flush=True)
    print(f"   📑 Themes: {themes_count.count}", flush=True)
    print("\n✅ Rebuild complete!", flush=True)


if __name__ == "__main__":
    main()
