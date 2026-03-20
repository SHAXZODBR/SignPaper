# -*- coding: utf-8 -*-
"""Check all analytics tables and stats view."""
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

print("=== Stats Overview View ===")
try:
    stats = client.table("stats_overview").select("*").execute()
    if stats.data:
        s = stats.data[0]
        print(f"  Books: {s.get('total_books')}")
        print(f"  Themes: {s.get('total_themes')}")
        print(f"  Resources: {s.get('total_resources')}")
        print(f"  Users: {s.get('total_users')}")
        print(f"  Downloads: {s.get('total_downloads')}")
        print(f"  Searches: {s.get('total_searches')}")
except Exception as e:
    print(f"View error: {e}")

print("\n=== Individual Table Counts ===")
tables = ["user_analytics", "search_analytics", "downloads", "support_messages", "feedback", "resources"]
for t in tables:
    try:
        r = client.table(t).select("id", count="exact").execute()
        print(f"{t}: {r.count}")
    except Exception as e:
        print(f"{t}: ERROR - {e}")

print("\n=== Recent Activity ===")
# Recent searches
try:
    recent = client.table("search_analytics").select("query, created_at").order("created_at", desc=True).limit(5).execute()
    print("Last 5 searches:")
    for r in recent.data:
        print(f"  - {r.get('query')} at {r.get('created_at')}")
except Exception as e:
    print(f"Search error: {e}")

# Recent users
try:
    users = client.table("user_analytics").select("telegram_username, action_type, created_at").order("created_at", desc=True).limit(5).execute()
    print("\nLast 5 user actions:")
    for u in users.data:
        print(f"  - @{u.get('telegram_username')} {u.get('action_type')}")
except Exception as e:
    print(f"User error: {e}")
