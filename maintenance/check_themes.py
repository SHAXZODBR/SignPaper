# Check themes data
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))
count = c.table('themes').select('id', count='exact').execute().count
print(f"Total themes in DB: {count}")

themes = c.table('themes').select('id, name_uz, start_page, end_page').limit(5).execute()
print("\nSample themes:")
for t in themes.data:
    print(f"ID {t['id']}: {t['name_uz']} | Pages {t['start_page']}-{t['end_page']}")
