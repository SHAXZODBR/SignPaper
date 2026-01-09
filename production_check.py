# -*- coding: utf-8 -*-
"""Production readiness check - test all tables and features."""
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

print("=" * 60)
print("SignPaper - Production Readiness Check")
print("=" * 60)

# Check all tables
print("\n[1] TABLE STATUS")
print("-" * 40)

tables = {
    "books": "Core data - school books",
    "themes": "Core data - book chapters",
    "user_analytics": "Tracks user actions",
    "search_analytics": "Tracks searches",
    "downloads": "Tracks PDF downloads",
    "support_messages": "User support messages",
    "feedback": "User ratings/feedback",
    "resources": "Additional resources (optional)",
}

all_ok = True
for table, desc in tables.items():
    try:
        r = client.table(table).select("id", count="exact").execute()
        status = "OK" if r.count is not None else "EMPTY"
        print(f"  {table}: {r.count} rows - {desc}")
    except Exception as e:
        print(f"  {table}: ERROR - {e}")
        all_ok = False

# Check stats view
print("\n[2] STATS OVERVIEW VIEW")
print("-" * 40)
try:
    stats = client.table("stats_overview").select("*").execute()
    if stats.data:
        s = stats.data[0]
        for k, v in s.items():
            print(f"  {k}: {v}")
except Exception as e:
    print(f"  ERROR: {e}")

# Test insert permissions
print("\n[3] INSERT PERMISSIONS TEST")
print("-" * 40)

test_tables = ["user_analytics", "search_analytics", "downloads", "support_messages", "feedback"]
for t in test_tables:
    try:
        if t == "user_analytics":
            data = {"telegram_user_id": 999999, "action_type": "test"}
        elif t == "search_analytics":
            data = {"query": "test", "results_count": 0}
        elif t == "downloads":
            data = {"telegram_user_id": 999999, "download_type": "test"}
        elif t == "support_messages":
            data = {"telegram_user_id": 999999, "message": "test"}
        elif t == "feedback":
            data = {"telegram_user_id": 999999, "rating": 5}
        
        result = client.table(t).insert(data).execute()
        # Clean up test data
        client.table(t).delete().eq("id", result.data[0]["id"]).execute()
        print(f"  {t}: OK (can insert)")
    except Exception as e:
        print(f"  {t}: FAILED - {e}")
        all_ok = False

# Check environment
print("\n[4] ENVIRONMENT CHECK")
print("-" * 40)
env_vars = {
    "TELEGRAM_BOT_TOKEN": os.getenv("TELEGRAM_BOT_TOKEN"),
    "SUPABASE_URL": os.getenv("SUPABASE_URL"),
    "SUPABASE_KEY": os.getenv("SUPABASE_KEY"),
    "ADMIN_CHAT_ID": os.getenv("ADMIN_CHAT_ID"),
    "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
}
for var, val in env_vars.items():
    if val:
        masked = val[:10] + "..." if len(val) > 10 else val
        print(f"  {var}: SET ({masked})")
    else:
        print(f"  {var}: NOT SET")
        if var in ["TELEGRAM_BOT_TOKEN", "SUPABASE_URL", "SUPABASE_KEY"]:
            all_ok = False

print("\n" + "=" * 60)
if all_ok:
    print("STATUS: PRODUCTION READY!")
else:
    print("STATUS: ISSUES FOUND - Check above")
print("=" * 60)
