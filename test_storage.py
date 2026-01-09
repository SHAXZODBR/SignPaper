# Test Supabase Storage access
from dotenv import load_dotenv
load_dotenv()
import os
from supabase import create_client

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

client = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"Connecting to: {SUPABASE_URL}")
try:
    buckets = client.storage.list_buckets()
    print("Available buckets:")
    for b in buckets:
        print(f" - {b.name} (ID: {b.id}, Public: {b.public})")
    
    # Try to list files in 'books' bucket
    files = client.storage.from_('books').list()
    print(f"\nFiles in 'books' bucket: {len(files)}")
    
    # Try a small test upload
    print("\nTesting small file upload...")
    test_data = b"Hello Supabase"
    res = client.storage.from_('books').upload(
        path="test_permission.txt",
        file=test_data,
        file_options={"content-type": "text/plain", "upsert": "true"}
    )
    print("✅ Test upload successful!")
    
    # Clean up
    client.storage.from_('books').remove(["test_permission.txt"])
    print("✅ Test cleanup successful!")

except Exception as e:
    print(f"❌ Error: {e}")
