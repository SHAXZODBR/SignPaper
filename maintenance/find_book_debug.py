# Find specific book
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
res = c.table('books').select('*').eq('grade', 6).ilike('subject', '%tarix%').execute()

print(f"Found {len(res.data)} books for Grade 6 History:")
for b in res.data:
    print("-" * 40)
    print(f"ID: {b['id']}")
    print(f"Title: {b['title_uz']}")
    print(f"Path UZ: {b['pdf_path_uz']}")
    print(f"Path RU: {b['pdf_path_ru']}")
