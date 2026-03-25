import os
import re
import sys
from pathlib import Path
import fitz
import requests
from supabase import create_client
from dotenv import load_dotenv

# Add project root to sys.path
sys.path.append(str(Path(__file__).parent.parent))

# Credentials
URL = 'https://rhjsndgajlvnhbzwayhc.supabase.co'
KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A'

client = create_client(URL, KEY)

def normalize_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def extract_text_from_range(doc, start_page: int, end_page: int, max_chars: int = 5000) -> str:
    """Extract text from a page range."""
    text_parts = []
    
    for page_num in range(start_page, min(end_page + 1, doc.page_count)):
        page = doc[page_num]
        text_parts.append(page.get_text("text"))
    
    full_text = "\n".join(text_parts)
    full_text = re.sub(r'\n{3,}', '\n\n', full_text)
    full_text = full_text.strip()
    
    if len(full_text) > max_chars:
        full_text = full_text[:max_chars] + "..."
    
    return full_text

def extract_themes_heuristic(pdf_path):
    """
    Heuristically find chapters/themes in a PDF.
    Returns list of dicts: {'name': str, 'start': int, 'end': int}
    """
    doc = fitz.open(pdf_path)
    themes = []
    
    # 1. Try TOC first
    toc = doc.get_toc()
    if toc:
        for i, (level, title, page) in enumerate(toc):
            start = page - 1
            # End is the start of next TOC item or last page
            end = (toc[i+1][2] - 2) if i < len(toc)-1 else (doc.page_count - 1)
            themes.append({
                'name': title,
                'start': max(0, start),
                'end': min(doc.page_count - 1, end)
            })
        if themes: 
            doc.close()
            return themes

    # 2. Heuristic mapping
    markers = []
    for page_num in range(doc.page_count):
        text = doc[page_num].get_text()
        patterns = [
            r'(\d+[- ]*bob)', r'(bob[- ]*\d+)',
            r'(\d+[- ]*глава)', r'(глава[- ]*\d+)',
            r'(§\s*\d+)',
            r'([IVX]+\s*bob)', r'(bob\s*[IVX]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                lines = text.split('\n')
                title = match.group(0)
                for line in lines:
                    if title in line:
                        title = normalize_text(line[:80])
                        break
                markers.append({'page': page_num, 'name': title})
                break
    
    if not markers:
        chunk_size = 15
        for i in range(0, doc.page_count, chunk_size):
            themes.append({
                'name': f"{i//chunk_size + 1}-mavzu",
                'start': i,
                'end': min(i + chunk_size - 1, doc.page_count - 1)
            })
    else:
        cleaned_markers = []
        last_page = -10
        for m in markers:
            if m['page'] > last_page + 1:
                cleaned_markers.append(m)
                last_page = m['page']
        
        for i, m in enumerate(cleaned_markers):
            start = m['page']
            end = cleaned_markers[i+1]['page'] - 1 if i < len(cleaned_markers)-1 else doc.page_count - 1
            themes.append({
                'name': m['name'],
                'start': start,
                'end': end
            })
            
    doc.close()
    return themes

def main():
    print("=" * 60)
    print("SignPaper - Smart Theme Extraction (Online)")
    print("=" * 60)
    
    books = client.table("books").select("*").execute().data
    print(f"Processing {len(books)} books.")
    
    total_added = 0
    temp_dir = Path("data/temp_extraction")
    temp_dir.mkdir(parents=True, exist_ok=True)
    
    for book in books:
        book_id = book['id']
        url = book.get('pdf_url_uz') or book.get('pdf_url_ru')
        is_uz = bool(book.get('pdf_url_uz'))
        subject = book.get('subject', '')
        grade = book.get('grade', 0)
        
        if not url:
            print(f"Skipping Book {book_id}: No PDF URL")
            continue
            
        print(f"\n[{book_id}] {subject} {grade}-sinf...")
        
        pdf_path = temp_dir / f"book_{book_id}.pdf"
        
        try:
            if not pdf_path.exists():
                resp = requests.get(url, timeout=60)
                if resp.status_code == 200:
                    with open(pdf_path, 'wb') as f:
                        f.write(resp.content)
                else:
                    print(f"  Download failed: {resp.status_code}")
                    continue
            
            themes = extract_themes_heuristic(str(pdf_path))
            print(f"  Found {len(themes)} distinct themes.")
            
            # Open PDF for content extraction
            doc = fitz.open(str(pdf_path))
            
            # Cleanup old themes for this book
            client.table("themes").delete().eq("book_id", book_id).execute()
            
            # Prepare batch
            batch = []
            for i, t in enumerate(themes):
                # Extract actual content for search/AI
                content = extract_text_from_range(doc, t['start'], t['end'])
                
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
                
            if batch:
                # Insert in chunks to avoid large payload errors
                for i in range(0, len(batch), 50):
                    client.table("themes").insert(batch[i:i+50]).execute()
                total_added += len(batch)
                print(f"  ✅ Re-extracted {len(batch)} themes.")
            
            doc.close()
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            
    print("\n" + "=" * 60)
    print(f"COMPLETED! Total themes re-extracted: {total_added}")

if __name__ == "__main__":
    main()
