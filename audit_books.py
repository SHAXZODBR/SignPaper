# Audit all books and their cloud readiness
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

BASE_DIR = r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books"
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"
client = create_client(SUPABASE_URL, SUPABASE_KEY)

books = client.table("books").select("id, title_uz, pdf_path_uz, grade, subject").execute().data

# Build local file cache for faster searching
local_files = []
for root, dirs, files in os.walk(BASE_DIR):
    for f in files:
        if f.lower().endswith('.pdf'):
            local_files.append({
                'name': f,
                'path': os.path.join(root, f),
                'size_mb': os.path.getsize(os.path.join(root, f)) / (1024 * 1024)
            })

results = []
for b in books:
    path = b.get('pdf_path_uz') or ""
    status = "MISSING"
    detail = ""
    
    if 'supabase' in path.lower():
        status = "CLOUD"
    elif path.startswith('http'):
        status = "EXTERNAL" # Eduportal or similar
    elif path and os.path.exists(path):
        size_mb = os.path.getsize(path) / (1024 * 1024)
        if size_mb > 50:
            status = "TOO_LARGE"
            detail = f"{size_mb:.1f}MB"
        else:
            status = "LOCAL_EXISTS"
    else:
        # Try finding it in local cache
        found = None
        # Try matching by filename keywords
        keywords = (b.get('title_uz') or b.get('subject') or "").lower().split()
        keywords = [k for k in keywords if len(k) > 3]
        grade = str(b.get('grade'))
        
        for lf in local_files:
            if grade in lf['name'] and all(k in lf['name'].lower() for k in keywords):
                found = lf
                break
        
        if found:
            if found['size_mb'] > 50:
                status = "TOO_LARGE"
                detail = f"{found['size_mb']:.1f}MB"
            else:
                status = "LOCAL_EXISTS"
                detail = found['path']
        else:
            status = "NOT_FOUND"

    results.append({
        'id': b['id'],
        'title': b['title_uz'],
        'status': status,
        'detail': detail
    })

# Print summary
stats = {}
for r in results:
    stats[r['status']] = stats.get(r['status'], 0) + 1

print("=== BOOK STATUS AUDIT ===")
for s, count in stats.items():
    print(f"{s}: {count}")

print("\n--- NON-CLOUD BOOKS ---")
for r in results:
    if r['status'] != "CLOUD":
        print(f"ID {r['id']}: {r['title']} | {r['status']} | {r['detail']}")
