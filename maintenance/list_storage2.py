# -*- coding: utf-8 -*-
"""List all files recursively in Supabase Storage bucket."""
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

def list_recursive(path="", depth=0):
    """List folder contents recursively."""
    indent = "  " * depth
    try:
        items = client.storage.from_(BUCKET_NAME).list(path)
        for item in items:
            name = item.get('name', '')
            full_path = f"{path}/{name}" if path else name
            
            if item.get('id'):  # It's a file
                url = client.storage.from_(BUCKET_NAME).get_public_url(full_path)
                print(f"{indent}FILE: {name}")
                print(f"{indent}  URL: {url[:100]}...")
            else:  # It's a folder
                print(f"{indent}FOLDER: {name}/")
                if depth < 3:  # Limit recursion
                    list_recursive(full_path, depth + 1)
    except Exception as e:
        print(f"{indent}Error: {e}")

print(f"Bucket: {BUCKET_NAME}")
print("=" * 60)
list_recursive()
