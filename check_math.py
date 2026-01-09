
import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

load_dotenv()
from database.supabase_client import get_supabase

def check_math5():
    client = get_supabase()
    
    # 1. Find book
    print("Finding Matematika 5 books...")
    books = client.table("books").select("*").ilike("subject", "%matem%").eq("grade", 5).execute()
    
    if not books.data:
        print("No Matematika 5 books found!")
        return

    for book in books.data:
        print(f"\nID: {book['id']} | Title: {book['title_uz'] or book['title_ru']}")
        
        # 2. Check themes
        themes = client.table("themes").select("name_uz, name_ru, content_uz").eq("book_id", book['id']).limit(5).execute()
        print(f"Themes count: {len(themes.data)}")
        for t in themes.data:
            print(f" - {t['name_uz'] or t['name_ru']}")
            if "Natural" in (t['content_uz'] or ""):
                print("   (Contains 'Natural')")

if __name__ == "__main__":
    check_math5()
