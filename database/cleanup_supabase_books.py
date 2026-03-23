from supabase import create_client
import os

SUPABASE_URL = "https://rhjsndgajlvnhbzwayhc.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"

def main():
    client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    print("Fetching all books...")
    res = client.table("books").select("*").execute()
    books = res.data
    print(f"Found {len(books)} books.")
    
    # Map by filename or title
    filename_map = {} # filename -> list of books
    
    for b in books:
        # Get identifier (prefer filename from pdf_path or title)
        identifier = None
        if b.get('pdf_path_uz'): identifier = os.path.basename(b['pdf_path_uz'].replace('\\', '/')).lower()
        elif b.get('pdf_path_ru'): identifier = os.path.basename(b['pdf_path_ru'].replace('\\', '/')).lower()
        elif b.get('title_uz'): identifier = b['title_uz'].lower()
        elif b.get('title_ru'): identifier = b['title_ru'].lower()
        
        if identifier:
            if identifier not in filename_map:
                filename_map[identifier] = []
            filename_map[identifier].append(b)
            
    # Merge strategy
    for identifier, dups in filename_map.items():
        if len(dups) > 1:
            print(f"Merging duplicates for: {identifier}")
            # Target is the one with the MOST data (prioritize pdf_url)
            target = sorted(dups, key=lambda x: (x.get('pdf_url_uz') or x.get('pdf_url_ru') is not None, x.get('id')), reverse=True)[0]
            others = [b for b in dups if b['id'] != target['id']]
            
            # Transfer PDF URLs to target if target lacks them
            updates = {}
            for o in others:
                if not target.get('pdf_url_uz') and o.get('pdf_url_uz'):
                    target['pdf_url_uz'] = o['pdf_url_uz']
                    updates['pdf_url_uz'] = o['pdf_url_uz']
                if not target.get('pdf_url_ru') and o.get('pdf_url_ru'):
                    target['pdf_url_ru'] = o['pdf_url_ru']
                    updates['pdf_url_ru'] = o['pdf_url_ru']
            if updates:
                client.table("books").update(updates).eq("id", target['id']).execute()
            
            # Transfer Themes from others to target
            for o in others:
                themes_res = client.table("themes").select("id").eq("book_id", o['id']).execute()
                if themes_res.data:
                    print(f"  Moving {len(themes_res.data)} themes from {o['id']} to {target['id']}")
                    client.table("themes").update({"book_id": target['id']}).eq("book_id", o['id']).execute()
                
                # Delete duplicate book
                # client.table("books").delete().eq("id", o['id']).execute()
                # print(f"  Deleted duplicate book {o['id']}")
                # Wait, deleting might be risky if we missed something. Let's just deactivate them.
                client.table("books").update({"is_active": False}).eq("id", o['id']).execute()
                print(f"  Deactivated duplicate book {o['id']}")

if __name__ == "__main__":
    main()
