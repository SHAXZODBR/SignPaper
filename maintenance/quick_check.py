# -*- coding: utf-8 -*-
"""Quick check of database after rebuild."""
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

# Counts
books = client.table("books").select("id", count="exact").execute()
themes = client.table("themes").select("id", count="exact").execute()

print(f"Books: {books.count}")
print(f"Themes: {themes.count}")

# Sample themes with "natural" in name
print("\n=== Themes containing 'natural' ===")
natural = client.table("themes").select("name_uz, name_ru, book_id").or_("name_uz.ilike.%natural%,name_ru.ilike.%natural%").limit(10).execute()
for t in natural.data:
    name = t.get('name_uz') or t.get('name_ru') or 'No name'
    print(f"  - {name[:70]}")

# Sample of 5th grade math themes
print("\n=== 5th Grade Math Themes ===")
math_books = client.table("books").select("id").eq("grade", 5).eq("subject", "matematika").execute()
for book in math_books.data[:2]:
    themes_data = client.table("themes").select("name_uz, name_ru").eq("book_id", book['id']).limit(5).execute()
    print(f"\nBook {book['id']}:")
    for t in themes_data.data:
        name = t.get('name_uz') or t.get('name_ru') or 'No name'
        print(f"  - {name[:60]}")
