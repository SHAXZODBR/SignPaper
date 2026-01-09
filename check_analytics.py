# -*- coding: utf-8 -*-
"""Check analytics tables."""
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

client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== Analytics Tables Status ===\n")

# Check user_analytics
try:
    ua = client.table("user_analytics").select("id", count="exact").execute()
    print(f"user_analytics: {ua.count} records")
except Exception as e:
    print(f"user_analytics: ERROR - {e}")

# Check search_analytics
try:
    sa = client.table("search_analytics").select("id", count="exact").execute()
    print(f"search_analytics: {sa.count} records")
except Exception as e:
    print(f"search_analytics: ERROR - {e}")

# Check downloads
try:
    dl = client.table("downloads").select("id", count="exact").execute()
    print(f"downloads: {dl.count} records")
except Exception as e:
    print(f"downloads: ERROR - {e}")

# Check support_messages
try:
    sm = client.table("support_messages").select("id", count="exact").execute()
    print(f"support_messages: {sm.count} records")
except Exception as e:
    print(f"support_messages: ERROR - {e}")

# Check resources
try:
    rs = client.table("resources").select("id", count="exact").execute()
    print(f"resources: {rs.count} records")
except Exception as e:
    print(f"resources: ERROR - {e}")

print("\n=== Last 5 Search Analytics ===")
try:
    recent = client.table("search_analytics").select("*").order("created_at", desc=True).limit(5).execute()
    for r in recent.data:
        print(f"  Query: {r.get('query')}, Results: {r.get('results_count')}")
except Exception as e:
    print(f"  ERROR: {e}")
