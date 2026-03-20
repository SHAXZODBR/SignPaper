# Check themes data in detail
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

c = create_client(os.getenv('SUPABASE_URL'), os.getenv('SUPABASE_KEY'))

# Check count of themes with names
res_uz = c.table('themes').select('id', count='exact').not_.is_('name_uz', 'null').execute()
res_ru = c.table('themes').select('id', count='exact').not_.is_('name_ru', 'null').execute()

print(f"Themes with Uzbek names: {res_uz.count}")
print(f"Themes with Russian names: {res_ru.count}")

# Show some Uzbek names
if res_uz.count > 0:
    print("\nSample Uzbek Themes:")
    themes = c.table('themes').select('id, name_uz, start_page, end_page').not_.is_('name_uz', 'null').limit(10).execute()
    for t in themes.data:
        print(f"ID {t['id']}: {t['name_uz']} (Pages {t['start_page']}-{t['end_page']})")

# Show some Russian names
if res_ru.count > 0:
    print("\nSample Russian Themes:")
    themes = c.table('themes').select('id, name_ru, start_page, end_page').not_.is_('name_ru', 'null').limit(10).execute()
    for t in themes.data:
        print(f"ID {t['id']}: {t['name_ru']} (Pages {t['start_page']}-{t['end_page']})")
