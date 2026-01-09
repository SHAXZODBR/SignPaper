# Check book PDF paths
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

client = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
books = client.table('books').select('id, title_uz, pdf_path_uz, pdf_path_ru').limit(5).execute()

print("Sample book PDF paths:")
for b in books.data:
    path_uz = b.get('pdf_path_uz') or 'None'
    path_ru = b.get('pdf_path_ru') or 'None'
    print(f"\nBook {b['id']}:")
    print(f"  UZ: {path_uz[:100]}...")
    print(f"  RU: {path_ru[:100]}...")
