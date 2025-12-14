"""
Book Processor Service - Updated for Subject Folders
Processes book PDFs organized by subject folders.
"""
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple
from tqdm import tqdm
import fitz
import sys
sys.path.append('..')
from config import BOOKS_DIR, DATABASE_PATH
from database.models import init_db, get_session, Book, Theme, Resource
from services.resource_finder import ResourceFinder


class BookProcessor:
    """Processes book PDFs and populates the database with themes."""
    
    # Subject name mappings (folder name -> subject code)
    SUBJECT_MAPPING = {
        'matematika': 'matematika',
        'math': 'matematika',
        'biologiya': 'biologiya',
        'biology': 'biologiya',
        'botanika': 'biologiya',
        'zoologiya': 'biologiya',
        'fizika': 'fizika',
        'physics': 'fizika',
        'kimyo': 'kimyo',
        'chemistry': 'kimyo',
        'geografiya': 'geografiya',
        'geography': 'geografiya',
        'tarix': 'tarix',
        'history': 'tarix',
        'informatika': 'informatika',
        'adabiyot': 'adabiyot',
        'ona_tili': 'ona_tili',
        'rus_tili': 'rus_tili',
        'ingliz_tili': 'ingliz_tili',
    }
    
    def __init__(self):
        self.session = get_session()
    
    def detect_subject_from_path(self, pdf_path: Path) -> str:
        """Detect subject from folder structure or filename."""
        # Check parent folder name
        parent_folder = pdf_path.parent.name.lower()
        if parent_folder in self.SUBJECT_MAPPING:
            return self.SUBJECT_MAPPING[parent_folder]
        
        # Check filename for subject keywords
        filename = pdf_path.stem.lower()
        for keyword, subject in self.SUBJECT_MAPPING.items():
            if keyword in filename:
                return subject
        
        return 'unknown'
    
    def detect_grade(self, filename: str) -> Optional[int]:
        """Detect grade level from filename."""
        # Match patterns like "5", "_5_", "5-sinf", "класс5"
        patterns = [
            r'[_\s](\d+)[_\s]',
            r'(\d+)[-_\s]?sinf',
            r'(\d+)[-_\s]?klass',
            r'(\d+)[-_\s]?класс',
            r'grade[-_\s]?(\d+)',
            r'[_\s](\d+)[_\s]',
            r'_(\d+)_',
        ]
        for pattern in patterns:
            match = re.search(pattern, filename.lower())
            if match:
                grade = int(match.group(1))
                if 1 <= grade <= 11:
                    return grade
        return 5  # Default
    
    def extract_chapters(self, pdf_path: str) -> List[dict]:
        """Extract chapters from PDF using pattern matching."""
        doc = fitz.open(pdf_path)
        chapters = []
        
        # Pattern to match chapter markers and capture title
        # Matches: "XX-§. Title", "XX- §. Title", "§ XX. Title"
        pattern = r'(\d+)\s*[-­]?\s*§[\.\s]*([^\n]{3,60})'
        
        for page_num in range(len(doc)):
            text = doc[page_num].get_text()
            
            for match in re.finditer(pattern, text, re.IGNORECASE):
                chapter_num = int(match.group(1))
                title = match.group(2).strip()
                
                # Clean title - remove leading dots/spaces, limit length
                title = re.sub(r'^[\.\s]+', '', title)
                title = title[:60].strip()
                
                # If title is too short or mostly numbers, try next line
                if len(title) < 5 or title.replace(' ', '').isdigit():
                    start_pos = match.end()
                    after_text = text[start_pos:start_pos+200]
                    lines = after_text.strip().split('\n')
                    for line in lines[:3]:
                        line = line.strip()
                        if len(line) >= 5 and not line.replace(' ', '').isdigit():
                            title = line[:60]
                            break
                
                if not title or len(title) < 3:
                    title = f"MAVZU {chapter_num}"
                
                chapters.append({
                    'num': chapter_num,
                    'name': f"{chapter_num}-§. {title}",
                    'page': page_num
                })
        
        doc.close()
        
        # Remove duplicates
        seen = set()
        unique = []
        for ch in chapters:
            if ch['num'] not in seen:
                seen.add(ch['num'])
                unique.append(ch)
        
        unique.sort(key=lambda x: x['page'])
        
        # Calculate end pages
        total_pages = len(fitz.open(pdf_path))
        for i, ch in enumerate(unique):
            if i + 1 < len(unique):
                ch['end_page'] = unique[i + 1]['page'] - 1
            else:
                ch['end_page'] = total_pages - 1
        
        return unique
    
    def scan_books_directory(self) -> List[Tuple[Path, str]]:
        """Scan for PDF files in the books directory structure."""
        books = []
        
        # Scan Uzbek books (with subject subfolders)
        uzbek_dir = BOOKS_DIR / "uzbek"
        if uzbek_dir.exists():
            for pdf_file in uzbek_dir.rglob("*.pdf"):
                books.append((pdf_file, 'uz'))
        
        # Scan Russian books
        russian_dir = BOOKS_DIR / "russian"
        if russian_dir.exists():
            for pdf_file in russian_dir.rglob("*.pdf"):
                books.append((pdf_file, 'ru'))
        
        return books
    
    def process_book(self, pdf_path: Path, language: str) -> Optional[Book]:
        """Process a single book PDF."""
        filename = pdf_path.stem
        subject = self.detect_subject_from_path(pdf_path)
        grade = self.detect_grade(filename)
        
        # Clean title from filename
        title = filename.replace('www.idum.uz__', '').replace('_', ' ').title()
        
        print(f"  Subject: {subject}, Grade: {grade}")
        
        # Check if book exists
        existing = self.session.query(Book).filter(
            Book.subject == subject,
            Book.grade == grade
        ).first()
        
        if existing:
            # Update paths
            if language == 'uz':
                existing.pdf_path_uz = str(pdf_path)
                existing.title_uz = title
            else:
                existing.pdf_path_ru = str(pdf_path)
                existing.title_ru = title
            self.session.commit()
            book = existing
        else:
            # Create new book
            book = Book(
                title_uz=title if language == 'uz' else None,
                title_ru=title if language == 'ru' else None,
                subject=subject,
                grade=grade,
                pdf_path_uz=str(pdf_path) if language == 'uz' else None,
                pdf_path_ru=str(pdf_path) if language == 'ru' else None
            )
            self.session.add(book)
            self.session.commit()
        
        # Extract chapters
        chapters = self.extract_chapters(str(pdf_path))
        print(f"  Found {len(chapters)} chapters")
        
        if chapters:
            # Clear old themes for this book
            self.session.query(Theme).filter(Theme.book_id == book.id).delete()
            self.session.commit()
            
            # Add themes
            doc = fitz.open(str(pdf_path))
            for ch in chapters:
                content = ""
                for p in range(ch['page'], min(ch['end_page'] + 1, len(doc))):
                    content += doc[p].get_text() + "\n"
                content = content[:10000]
                
                theme = Theme(
                    book_id=book.id,
                    name_uz=ch['name'] if language == 'uz' else None,
                    name_ru=ch['name'] if language == 'ru' else None,
                    content_uz=content if language == 'uz' else None,
                    content_ru=content if language == 'ru' else None,
                    start_page=ch['page'],
                    end_page=ch['end_page'],
                    chapter_number=str(ch['num'])
                )
                self.session.add(theme)
            
            self.session.commit()
            doc.close()
        
        return book
    
    def process_all_books(self) -> int:
        """Process all books in the directory."""
        books = self.scan_books_directory()
        
        if not books:
            print("No PDF files found.")
            print(f"Add books to: {BOOKS_DIR}")
            return 0
        
        processed = 0
        for pdf_path, language in tqdm(books, desc="Processing books"):
            try:
                print(f"\n📖 {pdf_path.name}")
                book = self.process_book(pdf_path, language)
                if book:
                    processed += 1
                    print(f"  ✅ Done")
            except Exception as e:
                print(f"  ❌ Error: {e}")
                self.session.rollback()
        
        return processed
    
    def get_stats(self) -> dict:
        """Get database statistics."""
        fresh = get_session()
        return {
            'books': fresh.query(Book).count(),
            'themes': fresh.query(Theme).count(),
            'resources': fresh.query(Resource).count()
        }


def main():
    """Main entry point."""
    print("🔧 Initializing database...")
    init_db()
    
    print("\n📚 Processing books...")
    processor = BookProcessor()
    processed = processor.process_all_books()
    
    stats = processor.get_stats()
    print(f"\n✅ Processing complete!")
    print(f"   Books: {stats['books']}")
    print(f"   Themes: {stats['themes']}")
    print(f"   Resources: {stats['resources']}")


if __name__ == "__main__":
    main()
