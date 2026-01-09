# Check book paths
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
books = c.table('books').select('id, pdf_path_uz, pdf_path_ru').execute()

print("Book path analysis:")
print("=" * 50)

supabase_count = 0
local_count = 0
none_count = 0

for b in books.data:
    uz = b.get('pdf_path_uz') or ""
    ru = b.get('pdf_path_ru') or ""
    
    path = uz or ru
    if 'supabase' in path.lower():
        supabase_count += 1
    elif '\\' in path or path.startswith('c:'):
        local_count += 1
    else:
        none_count += 1

print(f"Supabase URLs: {supabase_count}")
print(f"Local paths: {local_count}")
print(f"None/Empty: {none_count}")

print("\nSample with Supabase URLs:")
for b in books.data[:10]:
    ru = b.get('pdf_path_ru') or ""
    if 'supabase' in ru.lower():
        print(f"  Book {b['id']}: {ru[:70]}...")
