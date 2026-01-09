# -*- coding: utf-8 -*-
"""Check theme data completeness."""
import os
import sys
import codecs
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Check theme data completeness
print("=== Theme Data Completeness ===\n")

# Total themes
total = client.table("themes").select("id", count="exact").execute()
print(f"Total themes: {total.count}")

# Themes with name_uz
with_name_uz = client.table("themes").select("id", count="exact").not_.is_("name_uz", "null").execute()
print(f"With name_uz: {with_name_uz.count}")

# Themes with name_ru
with_name_ru = client.table("themes").select("id", count="exact").not_.is_("name_ru", "null").execute()
print(f"With name_ru: {with_name_ru.count}")

# Themes with content_uz
with_content_uz = client.table("themes").select("id", count="exact").not_.is_("content_uz", "null").execute()
print(f"With content_uz: {with_content_uz.count}")

# Themes with content_ru
with_content_ru = client.table("themes").select("id", count="exact").not_.is_("content_ru", "null").execute()
print(f"With content_ru: {with_content_ru.count}")

# Themes with start_page
with_start = client.table("themes").select("id", count="exact").not_.is_("start_page", "null").execute()
print(f"With start_page: {with_start.count}")

# Themes with end_page
with_end = client.table("themes").select("id", count="exact").not_.is_("end_page", "null").execute()
print(f"With end_page: {with_end.count}")

# Sample themes without name
print("\n=== Sample Themes Without name_uz ===")
no_name = client.table("themes").select("id, book_id, name_uz, name_ru, start_page, end_page").is_("name_uz", "null").limit(5).execute()
for t in no_name.data:
    print(f"  ID: {t['id']}, Book: {t['book_id']}, name_ru: {t.get('name_ru', 'None')[:50] if t.get('name_ru') else 'None'}")

# Sample complete themes
print("\n=== Sample Complete Themes ===")
complete = client.table("themes").select("id, book_id, name_uz, start_page, end_page").not_.is_("name_uz", "null").limit(5).execute()
for t in complete.data:
    name = t.get('name_uz') or 'No name'
    print(f"  ID: {t['id']}, Book: {t['book_id']}, Name: {name[:50]}, Pages: {t['start_page']}-{t['end_page']}")
