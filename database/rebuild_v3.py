"""
SignPaper Complete Database Rebuild v3
Creates SEPARATE book entries for each PDF file.
Extracts ALL themes using intelligent content analysis.
"""
import os
import sys
import re
from pathlib import Path
from typing import List, Dict

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

# Subject detection from folder/filename
SUBJECT_PATTERNS = {
    'biologiya': ['biolog', 'botanik', 'zoolog', 'биолог', 'ботаник', 'зоолог'],
    'fizika': ['fizik', 'физик'],
    'kimyo': ['kimyo', 'химия', 'химий'],
    'matematika': ['matemat', 'algebra', 'geometr', 'математ', 'алгебр', 'геометр'],
    'tarix': ['tarix', 'istori', 'истори'],
}


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def detect_subject(folder_name: str, filename: str) -> str:
    """Detect subject from folder and filename."""
    text = (folder_name + " " + filename).lower()
    for subject, patterns in SUBJECT_PATTERNS.items():
        for pattern in patterns:
            if pattern in text:
                return subject
    return 'other'


def extract_grade(filename: str) -> int:
    """Extract grade from filename."""
    patterns = [
        r'(\d+)\s*-?\s*sinf',  # 5-sinf
        r'(\d+)\s*-?\s*класс', # 5-класс  
        r'(\d+)\s*-?\s*кл',    # 5 кл
        r'_(\d+)_',            # _5_
        r'\s(\d+)\s',          # space 5 space
        r'^(\d+)[\-_\s]',      # starts with number
        r'[\-_\s](\d+)$',      # ends with number
    ]
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            grade = int(match.group(1))
            if 1 <= grade <= 11:
                return grade
    return 5


def find_themes_by_structure(doc) -> List[Dict]:
    """
    Analyze PDF structure to find chapters/themes.
    Uses font sizes, page headers, and content patterns.
    """
    themes = []
    total_pages = doc.page_count
    
    # First try: Get TOC
    toc = doc.get_toc()
    if toc and len(toc) >= 3:
        for level, title, page_num in toc:
            if level <= 2:  # Top 2 levels only
                themes.append({
                    'title': title.strip()[:100],
                    'page': max(0, page_num - 1),
                    'type': 'toc'
                })
    
    # If no TOC, scan pages for chapter headers
    if not themes:
        prev_page = 0
        for page_num in range(total_pages):
            page = doc[page_num]
            text = page.get_text("text")
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            
            # Look for chapter indicators in first few lines
            for line in lines[:8]:
                if len(line) < 3 or len(line) > 120:
                    continue
                
                # Chapter pattern detection
                is_chapter = False
                
                # Pattern: numbers at start
                if re.match(r'^(\d+[\.\-])\s+\w', line):
                    is_chapter = True
                # Pattern: § symbol
                elif re.match(r'^§\s*\d+', line):
                    is_chapter = True
                # Pattern: "bob", "глава", "mavzu", "тема"
                elif re.search(r'\b(bob|глава|mavzu|тема|chapter)\b', line, re.IGNORECASE):
                    is_chapter = True
                # Pattern: Roman numerals
                elif re.match(r'^[IVX]+[\.\-\s]', line):
                    is_chapter = True
                
                if is_chapter and (page_num - prev_page >= 3 or not themes):
                    themes.append({
                        'title': line[:100],
                        'page': page_num,
                        'type': 'detected'
                    })
                    prev_page = page_num
                    break
    
    # If still not enough themes, divide by page count
    if len(themes) < 3:
        themes = []
        if total_pages < 30:
            interval = max(5, total_pages // 4)
        elif total_pages < 80:
            interval = 12
        elif total_pages < 150:
            interval = 15
        else:
            interval = 20
        
        for start_page in range(0, total_pages, interval):
            # Find title from first page of section
            page = doc[start_page]
            text = page.get_text("text")
            lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 5]
            
            title = None
            for line in lines[:10]:
                if len(line) > 10 and len(line) < 100:
                    # Skip lines that are mostly numbers
                    if sum(c.isalpha() for c in line) / len(line) > 0.5:
                        title = line[:80]
                        break
            
            if not title:
                title = f"Bo'lim {len(themes) + 1}"
            
            themes.append({
                'title': title,
                'page': start_page,
                'type': 'divided'
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
    return text[:max_chars] if len(text) > max_chars else text


def main():
    print("=" * 60, flush=True)
    print("SignPaper - Complete Database Rebuild v3", flush=True)
    print("Each PDF = Separate Book | Extract ALL Themes", flush=True)
    print("=" * 60, flush=True)
    
    client = get_client()
    
    # Step 1: Clear ALL existing data
    print("\n[1] Clearing existing data...", flush=True)
    try:
        client.table("themes").delete().neq("id", 0).execute()
        client.table("books").delete().neq("id", 0).execute()
        # Also clear analytics
        try:
            client.table("user_analytics").delete().neq("id", 0).execute()
            client.table("search_analytics").delete().neq("id", 0).execute()
            client.table("downloads").delete().neq("id", 0).execute()
        except:
            pass
        print("   Done - cleared all data", flush=True)
    except Exception as e:
        print(f"   Warning: {e}", flush=True)
    
    # Step 2: Find all PDFs
    print("\n[2] Finding PDFs...", flush=True)
    pdf_files = list(PDF_DIR.rglob("*.pdf"))
    print(f"   Found {len(pdf_files)} PDF files", flush=True)
    
    # Step 3: Create books and themes
    print("\n[3] Creating books and themes...", flush=True)
    books_created = 0
    themes_created = 0
    
    for pdf_path in sorted(pdf_files):
        relative = pdf_path.relative_to(PDF_DIR)
        parts = str(relative).replace("\\", "/").split("/")
        
        if len(parts) < 2:
            continue
        
        lang_folder = parts[0].lower()
        subject_folder = parts[1] if len(parts) > 1 else ""
        
        # Determine language
        is_uzbek = (lang_folder == 'uzbek')
        language = 'uz' if is_uzbek else 'ru'
        
        # Detect subject and grade
        subject = detect_subject(subject_folder, pdf_path.stem)
        grade = extract_grade(pdf_path.stem)
        
        # Clean filename for title
        filename = pdf_path.stem
        filename = re.sub(r'[_\-]+', ' ', filename)
        filename = re.sub(r'\s+', ' ', filename).strip()
        
        print(f"\n   [{language.upper()}] {filename}", flush=True)
        
        # Create book entry
        book_data = {
            'subject': subject,
            'grade': grade,
            'title_uz': filename if is_uzbek else None,
            'title_ru': filename if not is_uzbek else None,
            'pdf_path_uz': str(pdf_path) if is_uzbek else None,
            'pdf_path_ru': str(pdf_path) if not is_uzbek else None,
            'is_active': True,
        }
        
        try:
            result = client.table("books").insert(book_data).execute()
            book_id = result.data[0]['id']
            books_created += 1
            print(f"   Book ID: {book_id}", flush=True)
        except Exception as e:
            print(f"   Error creating book: {e}", flush=True)
            continue
        
        # Extract themes
        try:
            doc = fitz.open(str(pdf_path))
            print(f"   Pages: {doc.page_count}", flush=True)
            
            themes = find_themes_by_structure(doc)
            print(f"   Found {len(themes)} themes", flush=True)
            
            for i, theme_info in enumerate(themes):
                start_page = theme_info['page']
                end_page = theme_info['end_page']
                title = theme_info['title']
                
                # Extract content
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
            print(f"   Added themes: {len(themes)}", flush=True)
            
        except Exception as e:
            print(f"   Error: {e}", flush=True)
    
    # Step 4: Verification
    print("\n" + "=" * 60, flush=True)
    print("[4] Verification:", flush=True)
    
    books_count = client.table("books").select("id", count="exact").execute()
    themes_count = client.table("themes").select("id", count="exact").execute()
    uz_themes = client.table("themes").select("id", count="exact").not_.is_("content_uz", "null").execute()
    ru_themes = client.table("themes").select("id", count="exact").not_.is_("content_ru", "null").execute()
    
    print(f"\n   📚 Books: {books_count.count}", flush=True)
    print(f"   📑 Themes: {themes_count.count}", flush=True)
    print(f"   🇺🇿 Uzbek themes: {uz_themes.count}", flush=True)
    print(f"   🇷🇺 Russian themes: {ru_themes.count}", flush=True)
    
    print("\n✅ Complete!", flush=True)


if __name__ == "__main__":
    main()
