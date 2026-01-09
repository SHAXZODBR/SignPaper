# -*- coding: utf-8 -*-
"""Test inserting into analytics tables to find permission issues."""
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

print(f"Using key type: {'SERVICE_KEY' if 'SUPABASE_SERVICE_KEY' in os.environ else 'ANON_KEY'}")

client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Test insert into each table
print("\n=== Testing Inserts ===\n")

# 1. user_analytics
print("1. user_analytics...")
try:
    result = client.table("user_analytics").insert({
        "telegram_user_id": 12345,
        "action_type": "test",
        "telegram_username": "test_user",
        "first_name": "Test"
    }).execute()
    print(f"   SUCCESS - ID: {result.data[0]['id']}")
except Exception as e:
    print(f"   FAILED: {e}")

# 2. search_analytics
print("2. search_analytics...")
try:
    result = client.table("search_analytics").insert({
        "telegram_user_id": 12345,
        "query": "test query",
        "results_count": 5
    }).execute()
    print(f"   SUCCESS - ID: {result.data[0]['id']}")
except Exception as e:
    print(f"   FAILED: {e}")

# 3. downloads
print("3. downloads...")
try:
    result = client.table("downloads").insert({
        "telegram_user_id": 12345,
        "book_id": 319,
        "download_type": "book_pdf"
    }).execute()
    print(f"   SUCCESS - ID: {result.data[0]['id']}")
except Exception as e:
    print(f"   FAILED: {e}")

# 4. feedback
print("4. feedback...")
try:
    result = client.table("feedback").insert({
        "telegram_user_id": 12345,
        "rating": 5,
        "message": "Test feedback"
    }).execute()
    print(f"   SUCCESS - ID: {result.data[0]['id']}")
except Exception as e:
    print(f"   FAILED: {e}")

# 5. support_messages
print("5. support_messages...")
try:
    result = client.table("support_messages").insert({
        "telegram_user_id": 12345,
        "message": "Test support message",
        "is_from_user": True
    }).execute()
    print(f"   SUCCESS - ID: {result.data[0]['id']}")
except Exception as e:
    print(f"   FAILED: {e}")

# 6. resources
print("6. resources...")
try:
    result = client.table("resources").insert({
        "theme_id": 5670,
        "type": "test",
        "title_uz": "Test resource"
    }).execute()
    print(f"   SUCCESS - ID: {result.data[0]['id']}")
except Exception as e:
    print(f"   FAILED: {e}")

print("\n=== Done ===")
