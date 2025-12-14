"""
PDF Processor Service
Handles extraction and generation of PDFs for school books.
Includes OCR support for scanned PDFs using Tesseract.
"""
import fitz  # PyMuPDF
from pathlib import Path
from typing import Optional, List, Tuple
import re
import sys
import io
sys.path.append('..')
from config import OUTPUT_DIR

# OCR imports (optional - graceful fallback if not installed)
try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR libraries not available. Install with: pip install pdf2image pytesseract")


class PDFProcessor:
    """Processes PDF books - extracts text, themes, and generates new PDFs."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.doc = None
    
    def open(self) -> bool:
        """Open the PDF document."""
        try:
            self.doc = fitz.open(self.pdf_path)
            return True
        except Exception as e:
            print(f"Error opening PDF: {e}")
            return False
    
    def close(self):
        """Close the PDF document."""
        if self.doc:
            self.doc.close()
            self.doc = None
    
    def get_page_count(self) -> int:
        """Get total number of pages."""
        if not self.doc:
            return 0
        return len(self.doc)
    
    def extract_text(self, start_page: int = 0, end_page: Optional[int] = None) -> str:
        """
        Extract text from PDF pages.
        
        Args:
            start_page: Starting page (0-indexed)
            end_page: Ending page (inclusive, 0-indexed). None means last page.
        
        Returns:
            Extracted text as string
        """
        if not self.doc:
            return ""
        
        if end_page is None:
            end_page = len(self.doc) - 1
        
        text_parts = []
        for page_num in range(start_page, min(end_page + 1, len(self.doc))):
            page = self.doc[page_num]
            # Try different extraction methods
            text = page.get_text("text")
            
            # If text is mostly garbage (non-printable chars), try "blocks" method
            if self._is_garbled_text(text):
                text = page.get_text("blocks")
                if isinstance(text, list):
                    text = "\n".join([block[4] for block in text if len(block) > 4 and isinstance(block[4], str)])
            
            # Clean the extracted text
            text = self._clean_text(text)
            text_parts.append(text)
        
        return "\n".join(text_parts)
    
    def _is_garbled_text(self, text: str) -> bool:
        """Check if text appears to be garbled/unreadable."""
        if not text or len(text) < 10:
            return True
        
        # Count readable characters (ASCII letters, Cyrillic, digits, common punctuation)
        readable = 0
        for char in text:
            # ASCII letters and digits
            if char.isalnum():
                readable += 1
            # Cyrillic characters
            elif '\u0400' <= char <= '\u04FF':
                readable += 1
            # Common punctuation and whitespace
            elif char in ' \n\t.,!?;:-()[]{}\'\"':
                readable += 1
        
        # If less than 30% of characters are readable, consider it garbled
        ratio = readable / len(text) if text else 0
        return ratio < 0.3
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text by removing control characters and normalizing whitespace."""
        if not text:
            return ""
        
        # Remove control characters except newlines and tabs
        cleaned = ""
        for char in text:
            if char == '\n' or char == '\t' or char >= ' ':
                cleaned += char
        
        # Normalize multiple spaces/newlines
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
        
        return cleaned.strip()
    
    def extract_toc(self) -> List[Tuple[int, str, int]]:
        """
        Extract table of contents.
        
        Returns:
            List of tuples: (level, title, page_number)
        """
        if not self.doc:
            return []
        
        toc = self.doc.get_toc()
        return [(level, title, page) for level, title, page in toc]
    
    def find_themes_from_toc(self) -> List[dict]:
        """
        Extract themes/chapters from table of contents.
        
        Returns:
            List of theme dictionaries with name, start_page, end_page
        """
        toc = self.extract_toc()
        if not toc:
            return []
        
        themes = []
        for i, (level, title, page) in enumerate(toc):
            # Determine end page (start of next item or end of document)
            if i + 1 < len(toc):
                end_page = toc[i + 1][2] - 1
            else:
                end_page = len(self.doc) - 1
            
            themes.append({
                'level': level,
                'name': title.strip(),
                'start_page': page - 1,  # Convert to 0-indexed
                'end_page': end_page,
                'chapter_number': self._extract_chapter_number(title)
            })
        
        return themes
    
    def _extract_chapter_number(self, title: str) -> Optional[str]:
        """Extract chapter number from title (e.g., '1.2', 'Chapter 3')."""
        # Match patterns like "1.", "1.2", "§1", "Chapter 1", "Глава 1", "Bob 1"
        patterns = [
            r'^(\d+(?:\.\d+)*)\.',  # 1. or 1.2.
            r'^§\s*(\d+)',  # §1
            r'^(?:Chapter|Глава|Bob)\s*(\d+)',  # Chapter/Глава/Bob 1
        ]
        for pattern in patterns:
            match = re.match(pattern, title, re.IGNORECASE)
            if match:
                return match.group(1)
        return None
    
    def extract_theme_pdf(
        self, 
        start_page: int, 
        end_page: int, 
        output_filename: str
    ) -> Optional[Path]:
        """
        Extract specific pages into a new PDF.
        
        Args:
            start_page: Starting page (0-indexed)
            end_page: Ending page (inclusive, 0-indexed)
            output_filename: Name for the output file
        
        Returns:
            Path to the generated PDF, or None if failed
        """
        if not self.doc:
            return None
        
        try:
            new_doc = fitz.open()
            new_doc.insert_pdf(
                self.doc, 
                from_page=start_page, 
                to_page=end_page
            )
            
            output_path = OUTPUT_DIR / output_filename
            new_doc.save(output_path)
            new_doc.close()
            
            return output_path
        except Exception as e:
            print(f"Error extracting theme PDF: {e}")
            return None
    
    @staticmethod
    def merge_pdfs(pdf_paths: List[Path], output_filename: str) -> Optional[Path]:
        """
        Merge multiple PDFs into one.
        
        Args:
            pdf_paths: List of paths to PDFs to merge
            output_filename: Name for the output file
        
        Returns:
            Path to the merged PDF, or None if failed
        """
        try:
            merged_doc = fitz.open()
            
            for pdf_path in pdf_paths:
                if pdf_path.exists():
                    doc = fitz.open(pdf_path)
                    merged_doc.insert_pdf(doc)
                    doc.close()
            
            output_path = OUTPUT_DIR / output_filename
            merged_doc.save(output_path)
            merged_doc.close()
            
            return output_path
        except Exception as e:
            print(f"Error merging PDFs: {e}")
            return None


def create_bilingual_theme_pdf(
    uz_pdf_path: str,
    ru_pdf_path: str,
    uz_start: int,
    uz_end: int,
    ru_start: int,
    ru_end: int,
    output_filename: str
) -> Optional[Path]:
    """
    Create a bilingual PDF with theme content in both Uzbek and Russian.
    
    The output will have Uzbek pages first, then Russian pages.
    """
    try:
        merged_doc = fitz.open()
        
        # Add Uzbek pages
        if Path(uz_pdf_path).exists():
            uz_doc = fitz.open(uz_pdf_path)
            merged_doc.insert_pdf(uz_doc, from_page=uz_start, to_page=uz_end)
            uz_doc.close()
        
        # Add Russian pages
        if Path(ru_pdf_path).exists():
            ru_doc = fitz.open(ru_pdf_path)
            merged_doc.insert_pdf(ru_doc, from_page=ru_start, to_page=ru_end)
            ru_doc.close()
        
        output_path = OUTPUT_DIR / output_filename
        merged_doc.save(output_path)
        merged_doc.close()
        
        return output_path
    except Exception as e:
        print(f"Error creating bilingual PDF: {e}")
        return None


if __name__ == "__main__":
    # Test with a sample PDF
    import sys
    if len(sys.argv) > 1:
        processor = PDFProcessor(sys.argv[1])
        if processor.open():
            print(f"Pages: {processor.get_page_count()}")
            print(f"TOC: {processor.extract_toc()}")
            print(f"Themes: {processor.find_themes_from_toc()}")
            processor.close()
