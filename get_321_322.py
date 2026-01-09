# Find paths for IDs 321, 322
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
books = c.table('books').select('id, title_uz, pdf_path_uz').in_('id', [321, 322]).execute().data
for b in books:
    print(f"ID {b['id']}: {b['title_uz']} | Path: {b['pdf_path_uz']}")
