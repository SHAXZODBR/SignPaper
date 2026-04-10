"""
PDF Processor Service
Handles extraction and generation of PDFs for school books.
Includes OCR support for scanned PDFs using Tesseract.
"""
# Try to import PyMuPDF (optional dependency)
try:
    import fitz
    FITZ_AVAILABLE = True
except ImportError:
    FITZ_AVAILABLE = False
    print("PyMuPDF (fitz) not available. PDF processing features will be limited.")

try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False
    print("pypdf not available. Pure python fallback disabled.")

from pathlib import Path
from typing import Optional, List, Tuple
import re
import sys
import io
sys.path.append('..')
from config import OUTPUT_DIR

# OCR and alternative extraction imports (optional - graceful fallback if not installed)
try:
    from pdf2image import convert_from_path
    import pytesseract
    from PIL import Image
    OCR_AVAILABLE = True
except ImportError:
    OCR_AVAILABLE = False
    print("OCR libraries not available. Install with: pip install pdf2image pytesseract")

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False
    print("pdfplumber not available. Alternative extraction disabled.")


class PDFProcessor:
    """Processes PDF books - extracts text, themes, and generates new PDFs."""
    
    def __init__(self, pdf_path: str):
        self.pdf_path = Path(pdf_path)
        self.doc = None
    
    def open(self) -> bool:
        """Open the PDF document."""
        if not FITZ_AVAILABLE:
            print("Cannot open PDF: PyMuPDF not available (using pypdf).")
            # If PYPDF is available, we can still process PDFs without opening self.doc
            return PYPDF_AVAILABLE
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
    
    def extract_text(self, start_page: int = 0, end_page: Optional[int] = None, use_ocr: bool = True) -> str:
        """
        Extract text from PDF pages using multiple methods and OCR fallback.
        """
        if not self.doc:
            return ""
        
        if end_page is None:
            end_page = len(self.doc) - 1
        
        text_parts = []
        for page_num in range(start_page, min(end_page + 1, len(self.doc))):
            page = self.doc[page_num]
            
            # Method 1: Standard text extraction
            text = page.get_text("text")
            
            # Method 2: If standard fails, try blocks
            if self._is_garbled_text(text):
                blocks = page.get_text("blocks")
                if blocks:
                    text = "\n".join([b[4] for b in blocks if len(b) > 4 and isinstance(b[4], str)])
            
            # Method 3: OCR Fallback if still garbled/empty and requested
            if use_ocr and OCR_AVAILABLE and self._is_garbled_text(text):
                ocr_text = self.extract_text_via_ocr(page_num)
                if ocr_text:
                    text = ocr_text
            
            # Method 4: pdfplumber fallback if still garbled/empty and available
            if self._is_garbled_text(text) and PDFPLUMBER_AVAILABLE:
                plumber_text = self.extract_text_via_pdfplumber(page_num)
                if plumber_text:
                    text = plumber_text
            
            # Clean the extracted text
            text = self._clean_text(text)
            text_parts.append(text)
        
        return "\n".join(text_parts)

    def extract_text_via_ocr(self, page_num: int) -> str:
        """Extract text from a single page using OCR."""
        if not OCR_AVAILABLE:
            return ""
        
        try:
            # Convert page to image
            # We use a relatively high DPI for better OCR
            images = convert_from_path(
                str(self.pdf_path),
                first_page=page_num + 1,
                last_page=page_num + 1,
                dpi=300
            )
            
            if not images:
                return ""
            
            # Run OCR on the image
            # Try multiple languages if possible (Uzbek/Russian)
            # Tesseract lang codes: rus, uzb
            text = pytesseract.image_to_string(images[0], lang='rus+uzb+eng')
            return text
        except Exception as e:
            print(f"OCR error on page {page_num}: {e}")
            return ""

    def extract_text_via_pdfplumber(self, page_num: int) -> str:
        """Extract text from a single page using pdfplumber."""
        if not PDFPLUMBER_AVAILABLE:
            return ""
        
        try:
            with pdfplumber.open(self.pdf_path) as pdf:
                page = pdf.pages[page_num]
                return page.extract_text() or ""
        except Exception as e:
            print(f"pdfplumber error on page {page_num}: {e}")
            return ""
    
    def _is_garbled_text(self, text: str) -> bool:
        """Check if text appears to be garbled/unreadable or empty."""
        if not text:
            return True
            
        clean_text = text.strip()
        if len(clean_text) < 20: # Very little text is often a sign of an image/scanned page
            return True
        
        # Count readable characters (ASCII letters, Cyrillic, digits, common punctuation)
        readable = 0
        for char in clean_text:
            if char.isalnum() or '\u0400' <= char <= '\u04FF' or char in ' \n\t.,!?;:-()[]{}\'\"':
                readable += 1
        
        # If less than 40% of characters are readable, consider it garbled
        ratio = readable / len(clean_text) if clean_text else 0
        return ratio < 0.4
    
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
        """
        output_path = OUTPUT_DIR / output_filename
        
        # Try PyMuPDF first if available
        if FITZ_AVAILABLE and self.doc:
            try:
                new_doc = fitz.open()
                new_doc.insert_pdf(
                    self.doc, 
                    from_page=start_page, 
                    to_page=end_page
                )
                
                new_doc.save(output_path)
                new_doc.close()
                return output_path
            except Exception as e:
                print(f"Error extracting theme PDF (fitz): {e}")

        # Fallback to pure Python pypdf
        if PYPDF_AVAILABLE:
            try:
                from pypdf import PdfReader, PdfWriter
                
                reader = PdfReader(str(self.pdf_path))
                writer = PdfWriter()
                
                # Handle bounds safely
                actual_end = min(end_page, len(reader.pages) - 1)
                for i in range(start_page, actual_end + 1):
                    writer.add_page(reader.pages[i])
                    
                with open(output_path, "wb") as f:
                    writer.write(f)
                    
                return output_path
            except Exception as e:
                print(f"Error extracting theme PDF (pypdf): {e}")
                
        return None
    
    @staticmethod
    def merge_pdfs(pdf_paths: List[Path], output_filename: str) -> Optional[Path]:
        """
        Merge multiple PDFs into one.
        """
        output_path = OUTPUT_DIR / output_filename
        
        # Try PyMuPDF
        if FITZ_AVAILABLE:
            try:
                merged_doc = fitz.open()
                for pdf_path in pdf_paths:
                    if pdf_path.exists():
                        doc = fitz.open(pdf_path)
                        merged_doc.insert_pdf(doc)
                        doc.close()
                merged_doc.save(output_path)
                merged_doc.close()
                return output_path
            except Exception as e:
                print(f"Error merging PDFs (fitz): {e}")

        # Fallback to pure Python pypdf
        if PYPDF_AVAILABLE:
            try:
                from pypdf import PdfReader, PdfWriter
                writer = PdfWriter()
                
                for pdf_path in pdf_paths:
                    if pdf_path.exists():
                        reader = PdfReader(str(pdf_path))
                        for page in reader.pages:
                            writer.add_page(page)
                            
                with open(output_path, "wb") as f:
                    writer.write(f)
                    
                return output_path
            except Exception as e:
                print(f"Error merging PDFs (pypdf): {e}")
                
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
    """
    output_path = OUTPUT_DIR / output_filename
    
    # Try PyMuPDF
    if FITZ_AVAILABLE:
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
            
            merged_doc.save(output_path)
            merged_doc.close()
            
            return output_path
        except Exception as e:
            print(f"Error creating bilingual PDF (fitz): {e}")

    # Fallback to pure Python pypdf
    if PYPDF_AVAILABLE:
        try:
            from pypdf import PdfReader, PdfWriter
            writer = PdfWriter()
            
            # Add Uzbek pages
            if Path(uz_pdf_path).exists():
                reader = PdfReader(str(uz_pdf_path))
                actual_end = min(uz_end, len(reader.pages) - 1)
                for i in range(uz_start, actual_end + 1):
                    writer.add_page(reader.pages[i])
                    
            # Add Russian pages
            if Path(ru_pdf_path).exists():
                reader = PdfReader(str(ru_pdf_path))
                actual_end = min(ru_end, len(reader.pages) - 1)
                for i in range(ru_start, actual_end + 1):
                    writer.add_page(reader.pages[i])
                    
            with open(output_path, "wb") as f:
                writer.write(f)
                
            return output_path
        except Exception as e:
            print(f"Error creating bilingual PDF (pypdf): {e}")
            
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
