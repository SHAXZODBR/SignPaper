"""Check 5th grade themes and test PDF generation."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()
from database.supabase_client import get_supabase

def check_5th_grade():
    client = get_supabase()
    
    # Get 5th grade books
    print("=== 5th Grade Books ===")
    books = client.table("books").select("id, title_uz, title_ru, subject, pdf_path_uz, pdf_path_ru").eq("grade", 5).execute()
    for book in books.data:
        print(f"Book ID: {book['id']}")
        print(f"  Title UZ: {book.get('title_uz')}")
        print(f"  Title RU: {book.get('title_ru')}")
        print(f"  Subject: {book.get('subject')}")
        print(f"  PDF UZ: {book.get('pdf_path_uz')}")
        print(f"  PDF RU: {book.get('pdf_path_ru')}")
        pdf_uz = book.get('pdf_path_uz')
        if pdf_uz:
            exists = Path(pdf_uz).exists()
            print(f"  PDF UZ Exists: {exists}")
        print()
    
    # Get themes for 5th grade
    print("\n=== 5th Grade Themes (search 'natural') ===")
    themes = client.table("themes").select(
        "id, name_uz, name_ru, start_page, end_page, book_id"
    ).ilike("name_uz", "%natural%").limit(10).execute()
    
    for t in themes.data:
        print(f"ID: {t['id']}, Book: {t['book_id']}")
        print(f"  Name: {t.get('name_uz') or t.get('name_ru')}")
        print(f"  Pages: {t.get('start_page')}-{t.get('end_page')}")
        print()
        
    # Count total themes for 5th grade math
    print("\n=== 5th Grade Math Theme Count ===")
    # First get math books for grade 5
    math_books = client.table("books").select("id").eq("grade", 5).eq("subject", "matematika").execute()
    print(f"5th grade math books: {len(math_books.data)}")
    for book in math_books.data:
        themes_count = client.table("themes").select("id", count="exact").eq("book_id", book['id']).execute()
        print(f"Book {book['id']} has {themes_count.count} themes")

if __name__ == "__main__":
    check_5th_grade()
