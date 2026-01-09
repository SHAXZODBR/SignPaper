"""
Complete Database Rebuild v2
Extracts themes from BOTH Uzbek AND Russian PDFs for each book.
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
PDF_DIR = Path(r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books")

SUBJECT_MAP = {
    'biologiya': 'biologiya', 'Biologiya': 'biologiya',
    'fizika': 'fizika', 'Fizika': 'fizika',
    'kimyo': 'kimyo', 'Kimyo': 'kimyo',
    'matematika': 'matematika', 'Matematika': 'matematika',
    'tarix': 'tarix', 'Tarix': 'tarix',
    'история': 'tarix', 'История': 'tarix',
    'биология': 'biologiya', 'Биология': 'biologiya',
    'физика': 'fizika', 'Физика': 'fizika',
    'химия': 'kimyo', 'Химия': 'kimyo',
    'математика': 'matematika', 'Математика': 'matematika',
}


def get_client():
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def extract_grade(filename: str) -> int:
    patterns = [
        r'(\d+)\s*-?\s*sinf', r'(\d+)\s*-?\s*кл', r'(\d+)\s*класс',
        r'[_\s](\d+)[_\s\.]', r'^(\d+)[_\-\s]', r'[_\-\s](\d+)$',
        r'_(\d+)_', r'(\d+)\s*-?\s*sinflar',
    ]
    for pattern in patterns:
        match = re.search(pattern, filename, re.IGNORECASE)
        if match:
            grade = int(match.group(1))
            if 1 <= grade <= 11:
                return grade
    return 5


def find_chapter_title(doc, start_page: int) -> str:
    if start_page >= doc.page_count:
        return None
    
    page = doc[start_page]
    text = page.get_text("text")
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    for line in lines[:15]:
        if len(line) < 4 or len(line) > 100:
            continue
        if re.match(r'^[\d\s\.\-,]+$', line):
            continue
        
        if re.match(r'^\d+[\.\-]?\s+\S', line):
            return line[:80]
        if re.match(r'^§\s*\d+', line):
            return line[:80]
        if 'bob' in line.lower() or 'глава' in line.lower():
            return line[:80]
        if 'mavzu' in line.lower() or 'тема' in line.lower():
            return line[:80]
        
        if len(line) > 12 and line[0].isalpha():
            alpha = sum(c.isalpha() or c.isspace() for c in line) / len(line)
            if alpha > 0.7:
                return line[:80]
    
    return None


def extract_text_range(doc, start: int, end: int, max_chars: int = 5000) -> str:
    parts = []
    for p in range(start, min(end + 1, doc.page_count)):
        parts.append(doc[p].get_text("text"))
    text = "\n".join(parts)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text[:max_chars] if len(text) > max_chars else text


def extract_themes_from_pdf(pdf_path: str, num_chapters: int = 8) -> list:
    """Extract themes from a PDF file."""
    themes = []
    try:
        doc = fitz.open(pdf_path)
        total_pages = doc.page_count
        
        if total_pages < 30:
            num_chapters = 3
        elif total_pages < 60:
            num_chapters = 5
        elif total_pages < 120:
            num_chapters = 8
        else:
            num_chapters = 10
        
        pages_per = total_pages // num_chapters
        
        for i in range(num_chapters):
            start = i * pages_per
            end = (i + 1) * pages_per - 1 if i < num_chapters - 1 else total_pages - 1
            
            title = find_chapter_title(doc, start)
            content = extract_text_range(doc, start, end)
            
            if len(content) >= 100:
                themes.append({
                    'order': i + 1,
                    'start_page': start,
                    'end_page': end,
                    'title': title,
                    'content': content
                })
        
        doc.close()
    except Exception as e:
        print(f"     Error: {e}", flush=True)
    
    return themes


def main():
    print("=" * 60, flush=True)
    print("SignPaper - Complete Rebuild v2 (Both Languages)", flush=True)
    print("=" * 60, flush=True)
    
    client = get_client()
    
    # Step 1: Clear all existing data
    print("\n1. Clearing existing data...", flush=True)
    try:
        client.table("themes").delete().neq("id", 0).execute()
        client.table("books").delete().neq("id", 0).execute()
        print("   Cleared all data", flush=True)
    except Exception as e:
        print(f"   Error: {e}", flush=True)
    
    # Step 2: Scan all PDFs and organize by subject+grade
    print("\n2. Scanning PDFs...", flush=True)
    pdf_map = {}  # (subject, grade) -> {'uz': path, 'ru': path}
    
    pdf_files = list(PDF_DIR.rglob("*.pdf"))
    print(f"   Found {len(pdf_files)} PDF files", flush=True)
    
    for pdf_path in pdf_files:
        relative = pdf_path.relative_to(PDF_DIR)
        parts = str(relative).replace("\\", "/").split("/")
        
        if len(parts) < 2:
            continue
        
        lang_folder = parts[0].lower()
        subject_folder = parts[1] if len(parts) > 1 else ""
        subject = SUBJECT_MAP.get(subject_folder, 'other')
        grade = extract_grade(pdf_path.stem)
        
        key = (subject, grade)
        if key not in pdf_map:
            pdf_map[key] = {'uz': None, 'ru': None}
        
        if lang_folder == 'uzbek':
            pdf_map[key]['uz'] = str(pdf_path)
        elif lang_folder == 'russian':
            pdf_map[key]['ru'] = str(pdf_path)
    
    print(f"   Organized into {len(pdf_map)} unique subject+grade combinations", flush=True)
    
    # Step 3: Create books and extract themes
    print("\n3. Creating books and extracting themes...", flush=True)
    books_created = 0
    themes_created = 0
    
    for (subject, grade), pdfs in sorted(pdf_map.items()):
        print(f"\n   [{subject} {grade}]", flush=True)
        
        # Create book
        book_data = {
            'subject': subject,
            'grade': grade,
            'title_uz': f"{subject.capitalize()} {grade}-sinf",
            'title_ru': f"{subject.capitalize()} {grade}-класс",
            'is_active': True,
        }
        
        try:
            result = client.table("books").insert(book_data).execute()
            book_id = result.data[0]['id']
            books_created += 1
        except Exception as e:
            print(f"   Error creating book: {e}", flush=True)
            continue
        
        # Extract themes from BOTH languages
        uz_themes = []
        ru_themes = []
        
        if pdfs['uz']:
            print(f"   Extracting from Uzbek PDF...", flush=True)
            uz_themes = extract_themes_from_pdf(pdfs['uz'])
            print(f"     Found {len(uz_themes)} chapters", flush=True)
        
        if pdfs['ru']:
            print(f"   Extracting from Russian PDF...", flush=True)
            ru_themes = extract_themes_from_pdf(pdfs['ru'])
            print(f"     Found {len(ru_themes)} chapters", flush=True)
        
        # Merge themes - use max chapters from either language
        num_themes = max(len(uz_themes), len(ru_themes))
        
        for i in range(num_themes):
            uz_theme = uz_themes[i] if i < len(uz_themes) else None
            ru_theme = ru_themes[i] if i < len(ru_themes) else None
            
            theme_data = {
                'book_id': book_id,
                'order_index': i + 1,
                'chapter_number': str(i + 1),
                'is_active': True,
            }
            
            # Fill Uzbek data
            if uz_theme:
                theme_data['name_uz'] = uz_theme['title'] or f"{i + 1}-bo'lim"
                theme_data['content_uz'] = uz_theme['content']
                theme_data['start_page'] = uz_theme['start_page']
                theme_data['end_page'] = uz_theme['end_page']
            
            # Fill Russian data
            if ru_theme:
                theme_data['name_ru'] = ru_theme['title'] or f"Глава {i + 1}"
                theme_data['content_ru'] = ru_theme['content']
                if 'start_page' not in theme_data:
                    theme_data['start_page'] = ru_theme['start_page']
                    theme_data['end_page'] = ru_theme['end_page']
            
            # Set defaults if missing
            if 'start_page' not in theme_data:
                theme_data['start_page'] = 0
                theme_data['end_page'] = 0
            if 'name_uz' not in theme_data:
                theme_data['name_uz'] = f"{i + 1}-bo'lim"
            if 'name_ru' not in theme_data:
                theme_data['name_ru'] = f"Глава {i + 1}"
            
            try:
                client.table("themes").insert(theme_data).execute()
                themes_created += 1
                
                name = theme_data.get('name_uz') or theme_data.get('name_ru') or 'N/A'
                print(f"     + {name[:45]}...", flush=True)
            except Exception as e:
                print(f"     Error: {e}", flush=True)
    
    # Step 4: Verify
    print("\n" + "=" * 60, flush=True)
    print("4. Verification:", flush=True)
    
    books_count = client.table("books").select("id", count="exact").execute()
    themes_count = client.table("themes").select("id", count="exact").execute()
    themes_with_uz = client.table("themes").select("id", count="exact").not_.is_("content_uz", "null").execute()
    themes_with_ru = client.table("themes").select("id", count="exact").not_.is_("content_ru", "null").execute()
    
    print(f"   Books: {books_count.count}", flush=True)
    print(f"   Themes: {themes_count.count}", flush=True)
    print(f"   Themes with Uzbek content: {themes_with_uz.count}", flush=True)
    print(f"   Themes with Russian content: {themes_with_ru.count}", flush=True)
    print("\nDone!", flush=True)


if __name__ == "__main__":
    main()
