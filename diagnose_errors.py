
import os
import sys
from dotenv import load_dotenv

if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'replace')

load_dotenv()
from database.supabase_client import _fallback_search, get_theme_with_book
from services.ai_summary import generate_summary

def run_diagnostics():
    print('--- SEARCH TEST ---')
    results = _fallback_search('sonlar', limit=1)
    if not results:
        print('No results found for "sonlar"')
        return

    theme_id = results[0]['theme_id']
    print(f'Found theme_id: {theme_id}')

    print('\n--- THEME FETCH TEST ---')
    theme = get_theme_with_book(theme_id)
    if theme:
        # Wrap logic similar to models.py
        print(f'Theme found: {theme.get("name_uz") or theme.get("name_ru")}')
        if theme.get('books'):
            print(f'Book linked: {theme["books"].get("title_uz") or theme["books"].get("title_ru")}')
        else:
            print('Book match FAILED (books field missing/empty)')
    else:
        print('Theme fetch FAILED (returned None)')

    print('\n--- AI TEST ---')
    try:
        content = "Natural sonlar deb sanashda ishlatiladigan sonlarga aytiladi. Masalan: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 va hokazo. Natural sonlar ustida qo'shish, ayirish, ko'paytirish va bo'lish amallarini bajarish mumkin. Eng kichik natural son 1 ga teng. Natural sonlar cheksizdir. Ular o'sish tartibida joylashgan. Har bir natural son o'zidan oldingi sondan 1 birlik kattadir."
        summary = generate_summary(content, 'Natural Sonlar', 'uz')
        print(f'Summary generated: {bool(summary)}')
        if summary:
            print(f'Content: {summary[:100]}...')
        else:
            print("Summary returned None")
    except Exception as e:
        print(f'AI Error: {e}')

if __name__ == "__main__":
    run_diagnostics()
