# Count books with Supabase URLs
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
books = c.table('books').select('id, pdf_path_uz, pdf_path_ru').execute()

good = 0
missing = []

for b in books.data:
    uz = b.get('pdf_path_uz') or ""
    ru = b.get('pdf_path_ru') or ""
    
    if 'supabase' in uz.lower() or 'supabase' in ru.lower():
        good += 1
    else:
        missing.append(b['id'])

print(f"Books with Supabase URLs: {good}")
print(f"Books missing: {len(missing)}")
print(f"Missing IDs: {missing}")
