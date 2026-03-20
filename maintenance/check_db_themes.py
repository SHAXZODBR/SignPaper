"""Check what themes actually exist in the database for 5th grade math."""
import os
from dotenv import load_dotenv

load_dotenv()
from database.supabase_client import get_supabase

def check_themes():
    client = get_supabase()
    
    # Get all 5th grade books
    print("=== 5th Grade Books ===")
    books = client.table("books").select("*").eq("grade", 5).execute()
    for book in books.data:
        print(f"Book ID: {book['id']}, Title: {book.get('title_uz')}")
    
    # Get themes for 5th grade
    print("\n=== Sample Themes (first 20) ===")
    themes = client.table("themes").select(
        "id, name_uz, name_ru, content_uz, start_page, end_page, book_id"
    ).limit(20).execute()
    
    for t in themes.data:
        name = t.get('name_uz') or t.get('name_ru') or 'No name'
        content_preview = (t.get('content_uz') or '')[:100].replace('\n', ' ')
        print(f"ID: {t['id']}, Name: {name[:50]}, Pages: {t.get('start_page')}-{t.get('end_page')}")
        if 'natural' in content_preview.lower():
            print(f"   ^ Contains 'natural' in content!")
            
    # Search for 'natural' in theme names
    print("\n=== Themes with 'natural' in NAME ===")
    natural_themes = client.table("themes").select("id, name_uz, name_ru").ilike("name_uz", "%natural%").execute()
    if natural_themes.data:
        for t in natural_themes.data:
            print(f"Found: {t.get('name_uz')}")
    else:
        print("No themes found with 'natural' in name_uz")
        
    # Search in content
    print("\n=== Themes with 'natural' in CONTENT ===")
    content_themes = client.table("themes").select("id, name_uz, book_id, content_uz").ilike("content_uz", "%natural%").limit(5).execute()
    for t in content_themes.data:
        print(f"ID: {t['id']}, Name: {t.get('name_uz')}, Book: {t['book_id']}")
        content = t.get('content_uz') or ''
        if 'natural' in content.lower():
            idx = content.lower().find('natural')
            print(f"   Content snippet: ...{content[max(0,idx-20):idx+40]}...")

if __name__ == "__main__":
    check_themes()
