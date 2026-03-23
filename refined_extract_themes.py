import sys
import os
import json
import re

# Add the installed library to path
sys.path.append('/tmp/lib')

try:
    import fitz
except ImportError:
    print("Error: fitz (PyMuPDF) not found in /tmp/lib")
    sys.exit(1)

def clean_text(text):
    return " ".join(text.split()).strip()

def extract_themes_from_book(pdf_path, grade, lang):
    try:
        doc = fitz.open(pdf_path)
    except Exception as e:
        print(f"Error opening {pdf_path}: {e}")
        return []

    themes = []
    
    # 1. Analyze base font size (body text)
    font_counts = {}
    for i in range(min(15, len(doc))):
        page = doc[i]
        blocks = page.get_text("dict")["blocks"]
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    for s in l["spans"]:
                        size = round(s["size"], 1)
                        font_counts[size] = font_counts.get(size, 0) + 1
    
    if not font_counts:
        return []
        
    body_font_size = sorted(font_counts.items(), key=lambda x: x[1], reverse=True)[0][0]
    
    # 2. Iterate through all pages
    # Patterns for titles
    patterns_uz = [
        r'^(BOB|MAVZU|PARAGRAF)',
        r'^(\d+\-§)',
        r'^(\d+\-BOB)',
        r'^(\d+\.\d+)',
        r'^§',
        r'^(\d+\.)\s+\w' 
    ]
    patterns_ru = [
        r'^(ГЛАВА|ТЕМА|ПАРАГРАФ)',
        r'^(\d+\-)',
        r'^§',
        r'^(\d+\.\d+)',
        r'^(\d+[\.§])\s+\w'
    ]
    
    all_patterns = patterns_uz + patterns_ru
    regex_title = re.compile("|".join(all_patterns), re.IGNORECASE)
    
    # Noise filters
    skip_keywords = ["mundarija", "оглавление", "содержание", "tuzuvchilar", "mualliflar", "copyright", "isbn", "vazirligi", "nashr", "министерство"]
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" in b:
                for l in b["lines"]:
                    # Merge spans in the line
                    line_text = " ".join([s["text"] for s in l["spans"]]).strip()
                    if not line_text:
                        continue
                        
                    # 1. Primary filter: Matching patterns
                    if regex_title.match(line_text):
                        # 2. Check font size or boldness
                        s_first = l["spans"][0]
                        size = round(s_first["size"], 1)
                        is_bold = "Bold" in s_first["font"] or "Semibold" in s_first["font"] or s_first["flags"] & 2
                        
                        if size >= body_font_size or is_bold:
                            # 3. Clean and filter by length
                            cleaned = clean_text(line_text)
                            
                            # Skip if contains dots (Mundarija)
                            if "........" in cleaned or "....." in cleaned:
                                continue
                                
                            # Skip common noise
                            cleaned_lower = cleaned.lower()
                            if any(k in cleaned_lower for k in skip_keywords):
                                continue
                            
                            if 5 < len(cleaned) < 300:
                                themes.append({
                                    "book": os.path.basename(pdf_path),
                                    "rel_path": os.path.relpath(pdf_path, "/home/shakhzodbtr/Desktop/SignPaper"),
                                    "grade": grade,
                                    "lang": lang,
                                    "page": page_num + 1,
                                    "title": cleaned
                                })

    return themes

def main():
    base_dir = "/home/shakhzodbtr/Desktop/SignPaper/books"
    all_extracted_themes = []
    
    config = [
        {"lang": "uz", "path": "uz/uz"},
        {"lang": "ru", "path": "ru/ru"}
    ]
    
    for conf in config:
        lang_dir = os.path.join(base_dir, conf["path"])
        if not os.path.exists(lang_dir):
            continue
            
        grades = [d for d in os.listdir(lang_dir) if os.path.isdir(os.path.join(lang_dir, d))]
        for grade in grades:
            grade_path = os.path.join(lang_dir, grade)
            files = [f for f in os.listdir(grade_path) if f.lower().endswith(".pdf")]
            for f in files:
                pdf_path = os.path.join(grade_path, f)
                print(f"Processing {f}...")
                themes = extract_themes_from_book(pdf_path, grade, conf["lang"])
                all_extracted_themes.extend(themes)
                
    with open("/home/shakhzodbtr/Desktop/SignPaper/extracted_themes_v2.json", "w", encoding="utf-8") as out:
        json.dump(all_extracted_themes, out, indent=2, ensure_ascii=False)
        
    print(f"\nDone! Extracted {len(all_extracted_themes)} themes to extracted_themes_v2.json")

if __name__ == "__main__":
    main()
