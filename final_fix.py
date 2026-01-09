# Update DB with GitHub URLs and fix remaining missing small books
import os
from dotenv import load_dotenv
load_dotenv()
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InJoanNuZGdhamx2bmhiendheWhjIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2NTY4NjI4NiwiZXhwIjoyMDgxMjYyMjg2fQ.8Z2t5HSAzm2MOvUpoP0r0EofmBZuFgdaVKwhq3CJc-A"
client = create_client(SUPABASE_URL, SUPABASE_KEY)

github_base = "https://raw.githubusercontent.com/SHAXZODBR/SignPaper/main/assets/large_books/"

# 1. Update Large Books
updates = [
    (380, "6-sinf_tarix.pdf"),
    (352, "botanika_6_uzb.pdf")
]

for book_id, filename in updates:
    url = github_base + filename
    print(f"Updating ID {book_id} -> {url}")
    client.table("books").update({
        "pdf_path_uz": url,
        "pdf_path_ru": url
    }).eq("id", book_id).execute()

# 2. Fix remaining small local books (IDs 321, 322 were mentioned in audit)
# Let's run a quick scan for them again
print("\nScanning for IDs 321, 322...")
res = client.table("books").select("id, title_uz, grade, subject").in_("id", [321, 322]).execute().data
# Search local folder for them
BASE_DIR = r"c:\Users\user\Downloads\Telegram Desktop\books (2)\books"
for b in res:
    print(f"Searching for {b['title_uz']} (Grade {b['grade']})...")
    found = None
    for root, dirs, files in os.walk(BASE_DIR):
        for f in files:
            if str(b['grade']) in f and ("algebra" in f.lower() or "geometriya" in f.lower()):
                found = os.path.join(root, f)
                break
        if found: break
    
    if found:
        # Upload to Supabase and update
        storage_path = f"uzbek/{f}"
        print(f"Found! Uploading to Supabase: {storage_path}")
        with open(found, 'rb') as f_obj:
            client.storage.from_("books").upload(path=storage_path, file=f_obj, file_options={"upsert": "true"})
        
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/books/{storage_path}"
        client.table("books").update({"pdf_path_uz": public_url, "pdf_path_ru": public_url}).eq("id", b['id']).execute()
        print(f"Updated ID {b['id']} successfully.")

print("\nCleanup complete.")
