
import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

load_dotenv()
from database.supabase_client import search_themes

def test():
    print("Testing search_themes...")
    try:
        results = search_themes("Natural sonlar", limit=5, offset=0)
        print(f"Results found: {len(results)}")
        for r in results:
            print(f" - {r.get('name_uz') or r.get('name_ru')}")
            
        print("\nTesting Pagination (Offset 5)...")
        results = search_themes("Natural sonlar", limit=5, offset=5)
        print(f"Results found: {len(results)}")
        
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
