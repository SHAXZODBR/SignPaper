"""
Complete Chapter Extractor
Scans PDF for all chapter headings in format XX-§ TITLE
"""
import fitz
import re
from pathlib import Path
import sys
sys.path.append('.')
from database.models import init_db, get_session, Book, Theme


def extract_all_chapters(pdf_path: str):
    """Extract all chapters from a Matematika PDF."""
    doc = fitz.open(pdf_path)
    chapters = []
    
    # Pattern: "XX-§" or "XX- §" with optional title
    pattern = r'(\d+)\s*-\s*§'
    
    for page_num in range(len(doc)):
        text = doc[page_num].get_text()
        
        # Find chapter markers
        for match in re.finditer(pattern, text):
            chapter_num = int(match.group(1))
            
            # Get text after the marker
            start_pos = match.end()
            after_text = text[start_pos:start_pos+300]
            
            # Extract title - look for uppercase words
            lines = after_text.strip().split('\n')
            title = ""
            for line in lines[:5]:
                line = line.strip()
                # Skip empty or very short lines
                if len(line) < 3:
                    continue
                # Check if line is mostly uppercase (a title)
                upper_count = sum(1 for c in line if c.isupper() or c in "''ʻ ")
                if upper_count > len(line) * 0.5 and len(line) > 3:
                    title = line
                    break
            
            if not title:
                title = f"MAVZU {chapter_num}"
            
            # Clean title
            title = ' '.join(title.split())
            
            chapters.append({
                'num': chapter_num,
                'name': f"{chapter_num}-§. {title}",
                'page': page_num
            })
    
    doc.close()
    
    # Remove duplicates - keep first occurrence of each chapter number
    seen = set()
    unique = []
    for ch in chapters:
        if ch['num'] not in seen:
            seen.add(ch['num'])
            unique.append(ch)
    
    # Sort by page number
    unique.sort(key=lambda x: x['page'])
    
    # Calculate end pages
    for i, ch in enumerate(unique):
        if i + 1 < len(unique):
            ch['end_page'] = unique[i + 1]['page'] - 1
        else:
            ch['end_page'] = len(fitz.open(pdf_path)) - 1
    
    return unique


def rebuild_themes_for_book(book_id: int):
    """Rebuild all themes for a book."""
    session = get_session()
    book = session.query(Book).filter(Book.id == book_id).first()
    
    if not book:
        print(f"Book {book_id} not found")
        return
    
    pdf_path = book.pdf_path_uz or book.pdf_path_ru
    if not pdf_path or not Path(pdf_path).exists():
        print(f"PDF not found: {pdf_path}")
        return
    
    print(f"\nProcessing: {Path(pdf_path).name}")
    print("=" * 50)
    
    # Extract chapters
    chapters = extract_all_chapters(pdf_path)
    print(f"Found {len(chapters)} chapters:\n")
    
    for ch in chapters:
        print(f"  {ch['name'][:50]} (pages {ch['page']+1}-{ch['end_page']+1})")
    
    # Delete old themes
    deleted = session.query(Theme).filter(Theme.book_id == book_id).delete()
    print(f"\nDeleted {deleted} old themes")
    session.commit()
    
    # Add new themes with content
    doc = fitz.open(pdf_path)
    language = 'uz' if book.pdf_path_uz else 'ru'
    
    for ch in chapters:
        # Extract content
        content = ""
        for p in range(ch['page'], min(ch['end_page'] + 1, len(doc))):
            content += doc[p].get_text() + "\n"
        content = content[:10000]
        
        theme = Theme(
            book_id=book_id,
            name_uz=ch['name'] if language == 'uz' else None,
            name_ru=ch['name'] if language == 'ru' else None,
            content_uz=content if language == 'uz' else None,
            content_ru=content if language == 'ru' else None,
            start_page=ch['page'],
            end_page=ch['end_page'],
            chapter_number=str(ch['num'])
        )
        session.add(theme)
    
    session.commit()
    doc.close()
    
    print(f"\nAdded {len(chapters)} new themes!")


if __name__ == "__main__":
    init_db()
    session = get_session()
    
    # Process all books with PDFs
    books = session.query(Book).filter(
        (Book.pdf_path_uz.isnot(None)) | (Book.pdf_path_ru.isnot(None))
    ).all()
    
    for book in books:
        rebuild_themes_for_book(book.id)
    
    # Count final themes
    total = session.query(Theme).count()
    print(f"\n{'='*50}")
    print(f"Total themes in database: {total}")
