# -*- coding: utf-8 -*-
"""List all files in Supabase Storage bucket."""
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
BUCKET_NAME = "books"

client = create_client(SUPABASE_URL, SUPABASE_KEY)

print(f"Listing files in bucket: {BUCKET_NAME}")
print("=" * 60)

try:
    # List root level
    items = client.storage.from_(BUCKET_NAME).list()
    print(f"\nRoot level items: {len(items)}")
    
    all_files = []
    
    for item in items:
        name = item.get('name', '')
        is_folder = item.get('id') is None
        
        if is_folder:
            print(f"\nFolder: {name}/")
            # List contents
            sub_items = client.storage.from_(BUCKET_NAME).list(name)
            for sub in sub_items[:5]:  # Show first 5 only
                sub_name = sub.get('name', '')
                if sub.get('id'):  # Is file
                    full_path = f"{name}/{sub_name}"
                    url = client.storage.from_(BUCKET_NAME).get_public_url(full_path)
                    print(f"  - {sub_name}")
                    print(f"    URL: {url[:80]}...")
                    all_files.append((full_path, url))
            if len(sub_items) > 5:
                print(f"  ... and {len(sub_items) - 5} more files")
        else:
            print(f"File: {name}")
            url = client.storage.from_(BUCKET_NAME).get_public_url(name)
            all_files.append((name, url))
    
    print(f"\n\nTotal files found: {len(all_files)}")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
