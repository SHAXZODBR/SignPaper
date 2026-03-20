# List details of missing books
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
books = c.table('books').select('id, title_uz, title_ru, pdf_path_uz, pdf_path_ru, grade, subject').execute()

missing = []

for b in books.data:
    uz = b.get('pdf_path_uz') or ""
    ru = b.get('pdf_path_ru') or ""
    
    if not ('supabase' in uz.lower() or 'supabase' in ru.lower()):
        missing.append({
            'id': b['id'],
            'title_uz': b.get('title_uz'),
            'title_ru': b.get('title_ru'),
            'pdf_path_uz': uz,
            'pdf_path_ru': ru,
            'grade': b.get('grade'),
            'subject': b.get('subject')
        })

print(f"Total missing: {len(missing)}")
for m in missing:
    path = m['pdf_path_uz'] or m['pdf_path_ru'] or "NONE"
    filename = path.split('\\')[-1] if '\\' in path else path
    print(f"ID: {m['id']} | Title: {m['title_uz'] or m['title_ru']} | File: {filename} | Subject: {m['subject']} | Grade: {m['grade']}")
