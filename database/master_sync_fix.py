import os
import sys
import subprocess
import re
from pathlib import Path
from supabase import create_client

# Constants
SUPABASE_URL = "https://rhjsndgajlvnhbzwayhc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"
BOOKS_ROOT = Path("books/uz/uz")

def transliterate_russian(text):
    trans_map = {
        'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
        'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
        'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
        'ф': 'f', 'х': 'kh', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
        'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya'
    }
    return "".join(trans_map.get(c.lower(), c) for c in text)

def safe_path(filename):
    # Mimic the upload_books_v2 safe_path logic
    safe = transliterate_russian(filename)
    safe = safe.replace(' ', '_')
    # Replace anything NOT alnum or ._-/ with _
    safe = "".join(c if c.isalnum() or c in '._-/' else '_' for c in safe)
    while '__' in safe:
        safe = safe.replace('__', '_')
    return safe

def compress_pdf(inp, outp):
    print(f"Aggressively compressing {inp}...")
    cmd = [
        "gs", "-sDEVICE=pdfwrite", "-dCompatibilityLevel=1.4",
        "-dPDFSETTINGS=/screen", "-dNOPAUSE", "-dQUIET", "-dBATCH",
        f"-sOutputFile={outp}", str(inp)
    ]
    subprocess.run(cmd, check=True)

def main():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Missing books I identified
    targets = [
        {"id": 1170, "file": "10/10рус (3).pdf", "lang": "uz"}, # It's Russian but the DB record 1170 expects it in UZ
        {"id": 1254, "file": "6/6рус.pdf", "lang": "uz"},
        {"id": 1289, "file": "7/рус (1).pdf", "lang": "uz"},
        {"id": 1332, "file": "8/8-sinf õzbekiston tarixi.pdf", "lang": "uz"},
        {"id": 1227, "file": "6/6-sinf Tarix yangi darslik..pdf", "lang": "uz"}
    ]
    
    # Add others that were over 50MB in my previous find results
    extra_files = [
        "7/7-sinf Geometriya yangi darslik..pdf",
        "10/Tarbiya 10-sinf UZ.pdf",
        "6/6-Sinflar uchun Matematikadan yangi darslik 2022-yil.pdf"
    ]
    
    # For extra files, I'll need to find their IDs.
    # Actually, I'll just focus on the active ones missing links first.
    
    for t in targets:
        local_path = BOOKS_ROOT / t["file"]
        if not local_path.exists():
            print(f"Skipping {local_path} (not found)")
            continue
            
        size_mb = local_path.stat().st_size / (1024*1024)
        print(f"\nProcessing ID {t['id']} | {t['file']} | {size_mb:.1f}MB")
        
        up_path = local_path
        if size_mb > 50:
            tmp_path = f"/tmp/compressed_{t['id']}.pdf"
            compress_pdf(local_path, tmp_path)
            up_path = Path(tmp_path)
            new_size = up_path.stat().st_size / (1024*1024)
            print(f"Compressed to {new_size:.1f}MB")
            if new_size > 50:
                 print("WARNING: Still > 50MB. Attempting grayscale...")
                 # try more aggressive grayscale?
                 
        # Upload
        storage_rel = f"uz/uz/{t['file']}"
        s_path = safe_path(storage_rel)
        print(f"Uploading to storage path: {s_path}")
        
        try:
            with open(up_path, "rb") as f:
                client.storage.from_("books").upload(s_path, f.read(), file_options={"upsert": "true", "content-type": "application/pdf"})
            
            url = client.storage.from_("books").get_public_url(s_path)
            col = f"pdf_url_{t['lang']}"
            client.table("books").update({col: url}).eq("id", t["id"]).execute()
            print(f"SUCCESS: Updated DB with {url}")
        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            if up_path != local_path and up_path.exists():
                up_path.unlink()

    print("\nMaster Sync Complete.")

if __name__ == "__main__":
    main()
