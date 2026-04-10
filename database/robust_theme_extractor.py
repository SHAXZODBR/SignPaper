import os
import re
import sys
from pathlib import Path
import fitz
import requests
from supabase import create_client
from dotenv import load_dotenv
from typing import List, Dict, Any, Optional

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Load environment
load_dotenv()

# Configuration from config.py or environment
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://rhjsndgajlvnhbzwayhc.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A")

client = create_client(SUPABASE_URL, SUPABASE_KEY)

def normalize_text(text: str) -> str:
    """Normalize text by removing extra spaces and newlines."""
    if not text: return ""
    return re.sub(r'\s+', ' ', text).strip()

def get_toc_candidates(doc: fitz.Document) -> List[Dict[str, Any]]:
    """Strategy 1: Extract themes from PDF Table of Contents."""
    candidates = []
    toc = doc.get_toc()
    if toc:
        for level, title, page in toc:
            if level <= 2: # Keep main chapters and sections
                candidates.append({
                    'name': title.strip(),
                    'page': page - 1, # 0-indexed
                    'source': 'toc',
                    'confidence': 1.0 if level == 1 else 0.8
                })
    return candidates

from services.pdf_processor import PDFProcessor, FITZ_AVAILABLE, OCR_AVAILABLE

def get_regex_candidates(doc: fitz.Document, processor: PDFProcessor) -> List[Dict[str, Any]]:
    """Strategy 2: Scan pages for chapter/section markers."""
    candidates = []
    
    # Common patterns in Uzbek/Russian textbooks
    patterns = [
        r'^(?:\d+[- ]*)?bob[:\s]+(.+)$',           # Bob 1: Title
        r'^(?:\d+[- ]*)?глава[:\s]+(.+)$',       # Глава 1: Title
        r'^§\s*(\d+)\.?\s*(.+)$',                 # §1 Title
        r'^(\d+)\s*-\s*§\.?\s*(.+)$',            # 1-§ Title
        r'^(?:mavzu|тема)\s*(\d+)?\.?[:\s]*(.+)$', # Mavzu 1: Title
        r'^(\d+\.\d+\.?)\s+([A-ZА-Я].+)$',        # 1.1. Title (starts with upper)
        r'^(ҚИСМ|ЧАСТЬ)\s*(\d+)?\.?[:\s]*(.+)$', # Qism 1
    ]
    
    for page_num in range(doc.page_count):
        # We only check the first 1/4 of the page for titles
        page = doc[page_num]
        blocks = page.get_text("blocks")
        
        # If no blocks found, try OCR
        if not blocks and OCR_AVAILABLE:
            ocr_text = processor.extract_text_via_ocr(page_num)
            if ocr_text:
                # Create a pseudo-block for regex matching
                blocks = [(0, 0, 0, 0, ocr_text)]
        
        if not blocks: continue
        
        # Sort blocks by vertical position
        blocks.sort(key=lambda b: b[1])
        
        for b in blocks[:8]: # Check top 8 blocks
            text = b[4].strip()
            if not text: continue
            
            lines = [l.strip() for l in text.split('\n') if l.strip()]
            if not lines: continue
            
            # Check the first line of the block
            first_line = lines[0]
            for pattern in patterns:
                match = re.match(pattern, first_line, re.IGNORECASE)
                if match:
                    title = match.group(0)
                    # If match has multiple groups, try to reconstruct a cleaner title
                    if len(match.groups()) > 1:
                        g1, g2 = match.groups()
                        if g2 and len(g2) > 3:
                            title = f"{g1}. {g2}" if '§' in first_line else g2
                    
                    candidates.append({
                        'name': normalize_text(title[:100]),
                        'page': page_num,
                        'source': 'regex' + ('_ocr' if not page.get_text("text") else ''),
                        'confidence': 0.7
                    })
                    break
    return candidates

def get_visual_candidates(doc: fitz.Document, processor: PDFProcessor) -> List[Dict[str, Any]]:
    """Strategy 3: Detect headings based on font size and weight."""
    candidates = []
    
    for page_num in range(doc.page_count):
        page = doc[page_num]
        dict_text = page.get_text("dict")
        
        # If no text found, visual strategy is impossible without OCR-based layout analysis
        # For now, we rely on Regex + OCR fallback if visual fails here
        if not dict_text["blocks"]:
             continue
             
        # Calculate average font size on page to detect outliers
        font_sizes = []
        for block in dict_text["blocks"]:
            if "lines" not in block: continue
            for line in block["lines"]:
                for span in line["spans"]:
                    font_sizes.append(span["size"])
        
        if not font_sizes: continue
        avg_size = sum(font_sizes) / len(font_sizes)
        header_threshold = avg_size * 1.3
        
        # Find lines with large or bold fonts at the top of the page
        for block in dict_text["blocks"][:8]: # Check top 8 blocks
             if "lines" not in block: continue
             
             # Heuristic: A block with a header should usually be short (1-2 lines)
             if len(block["lines"]) > 3: continue
             
             for line in block["lines"]:
                 line_text = ""
                 max_span_size = 0
                 is_bold = False
                 for span in line["spans"]:
                     text = span["text"].strip()
                     if not text: continue
                     
                     max_span_size = max(max_span_size, span["size"])
                     if span["flags"] & 2**4: # Bold
                         is_bold = True
                     line_text += text + " "
                 
                 line_text = line_text.strip()
                 
                 # Filtering rules
                 if not line_text or len(line_text) < 5 or len(line_text) > 120: continue
                 if line_text[0].islower(): continue # Headers don't start with lowercase
                 if line_text.endswith(('.', '!', '?')) and not re.match(r'^\d+\.', line_text): 
                     # Most headers don't end with period, unless they are numbered
                     if len(line_text) > 40: continue 
                 
                 if max_span_size > header_threshold or (is_bold and max_span_size > avg_size):
                     candidates.append({
                         'name': normalize_text(line_text),
                         'page': page_num,
                         'source': 'visual',
                         'confidence': 0.5
                     })
                     break # Only one visual header per page
             else:
                 continue
             break
             
    return candidates

def merge_candidates(candidates: List[Dict[str, Any]], page_count: int) -> List[Dict[str, Any]]:
    """Merge candidates from different strategies and resolve conflicts."""
    if not candidates: return []
    
    # Sort by page
    candidates.sort(key=lambda x: x['page'])
    
    merged = []
    
    # Group by page (or very close pages)
    current_group = [candidates[0]]
    for i in range(1, len(candidates)):
        prev = candidates[i-1]
        curr = candidates[i]
        
        if curr['page'] <= prev['page'] + 1: # Within 1 page
            current_group.append(curr)
        else:
            # Process old group
            best = max(current_group, key=lambda x: (x['confidence'], len(x['name'])))
            merged.append(best)
            current_group = [curr]
    
    # Last group
    if current_group:
        best = max(current_group, key=lambda x: (x['confidence'], len(x['name'])))
        merged.append(best)
        
    # Final cleanup: ensure uniqueness of pages and sensible ranges
    final = []
    last_page = -1
    for m in merged:
        if m['page'] > last_page:
            final.append(m)
            last_page = m['page']
            
    # Calculate end pages
    for i in range(len(final)):
        start = final[i]['page']
        end = final[i+1]['page'] - 1 if i < len(final) - 1 else page_count - 1
        final[i]['start'] = start
        final[i]['end'] = end
        
    return final

def process_book(book_id: int):
    """Run robust extraction on a specific book and sync to Supabase."""
    book = client.table("books").select("*").eq("id", book_id).single().execute().data
    if not book:
        print(f"Book {book_id} not found.")
        return
    
    url = book.get('pdf_url_uz') or book.get('pdf_url_ru') or book.get('pdf_path_uz') or book.get('pdf_path_ru')
    if not url:
        print(f"Book {book_id} has no PDF URL/path.")
        return
        
    is_uz = bool(book.get('pdf_url_uz') or book.get('pdf_path_uz'))
    
    temp_path = Path(f"data/temp_robust_{book_id}.pdf")
    temp_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Download if online
        if url.startswith('http'):
            if not temp_path.exists():
                print(f"Downloading {url}...")
                resp = requests.get(url, timeout=300)
                with open(temp_path, 'wb') as f:
                    f.write(resp.content)
            pdf_path = str(temp_path)
        else:
            pdf_path = url

        processor = PDFProcessor(pdf_path)
        if not processor.open():
            print(f"Could not open PDF: {pdf_path}")
            return
            
        doc = processor.doc
        print(f"Extracting themes for '{book.get('title_uz') or book.get('title_ru')}'...")
        
        # Collect candidates
        all_candidates = []
        all_candidates.extend(get_toc_candidates(doc))
        all_candidates.extend(get_regex_candidates(doc, processor))
        all_candidates.extend(get_visual_candidates(doc, processor))
        
        print(f"Found {len(all_candidates)} raw candidates across {len(doc)} pages.")
        
        # Merge and refine
        themes = merge_candidates(all_candidates, doc.page_count)
        print(f"Refined to {len(themes)} distinct themes.")
        
        if not themes:
            # Fallback to chunking if even robust methods fail
            print("WARNING: No themes found. Using fallback chunking.")
            chunk_size = 15
            for i in range(0, doc.page_count, chunk_size):
                themes.append({
                    'name': f"Mavzu {i//chunk_size + 1}",
                    'start': i,
                    'end': min(i + chunk_size - 1, doc.page_count - 1),
                    'source': 'fallback'
                })

        # Cleanup old themes
        client.table("themes").delete().eq("book_id", book_id).execute()
        
        # Prepare batch
        batch = []
        for i, t in enumerate(themes):
            # Use improved extraction from processor
            content = processor.extract_text(t['start'], t['end'])
            
            theme_data = {
                'book_id': book_id,
                'order_index': i + 1,
                'start_page': t['start'],
                'end_page': t['end'],
                'chapter_number': str(i + 1)
            }
            
            if is_uz:
                theme_data['name_uz'] = t['name']
                theme_data['content_uz'] = content
            else:
                theme_data['name_ru'] = t['name']
                theme_data['content_ru'] = content
                
            batch.append(theme_data)
        
        # Insert batch
        if batch:
            for i in range(0, len(batch), 50):
                client.table("themes").insert(batch[i:i+50]).execute()
            print(f"✅ Successfully synced {len(batch)} themes.")
            
        processor.close()
        
    except Exception as e:
        print(f"❌ Error processing book {book_id}: {e}")
        import traceback
        traceback.print_exc()

def process_local_file(pdf_path: str):
    """Run robust extraction on a local PDF file for testing."""
    if not Path(pdf_path).exists():
        print(f"File not found: {pdf_path}")
        return
        
    try:
        processor = PDFProcessor(pdf_path)
        if not processor.open():
            print(f"Could not open PDF: {pdf_path}")
            return
            
        doc = processor.doc
        print(f"\nProcessing local file: {pdf_path}")
        print(f"Pages: {doc.page_count}")
        
        # Collect candidates
        all_candidates = []
        all_candidates.extend(get_toc_candidates(doc))
        all_candidates.extend(get_regex_candidates(doc, processor))
        all_candidates.extend(get_visual_candidates(doc, processor))
        
        print(f"Found {len(all_candidates)} raw candidates.")
        
        # Merge and refine
        themes = merge_candidates(all_candidates, doc.page_count)
        print(f"Refined to {len(themes)} distinct themes:")
        
        for i, t in enumerate(themes[:20]): # Show first 20
            print(f"  {i+1}. {t['name'][:60]:<60} | Pages {t['start']+1}-{t['end']+1} | Source: {t['source']}")
        
        if len(themes) > 20:
            print(f"  ... and {len(themes)-20} more.")
            
        processor.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--book_id", type=int, help="Single book ID to process")
    parser.add_argument("--all", action="store_true", help="Process all books")
    parser.add_argument("--local", type=str, help="Local PDF path for testing")
    args = parser.parse_args()
    
    if args.local:
        process_local_file(args.local)
    elif args.book_id:
        process_book(args.book_id)
    elif args.all:
        books = client.table("books").select("id").execute().data
        for b in books:
            process_book(b['id'])
    else:
        print("Please specify --book_id ID or --all")
