import sys
import socket
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def check_hostname(hostname):
    print(f"--- Checking hostname: {hostname} ---")
    try:
        ip = socket.gethostbyname(hostname)
        print(f"✅ Hostname resolved to: {ip}")
        return True
    except socket.gaierror:
        print(f"❌ Could not resolve hostname: {hostname}")
        print("   Tips: Check your internet connection or DNS settings.")
        return False

def check_url(url):
    print(f"\n--- Checking URL: {url} ---")
    try:
        response = requests.get(url, timeout=10)
        print(f"✅ Successfully connected. Status code: {response.status_code}")
        return True
    except Exception as e:
        print(f"❌ Failed to connect to {url}")
        print(f"   Error: {e}")
        return False

if __name__ == "__main__":
    url = os.getenv("SUPABASE_URL", "https://rhjsndgajlvnhbzwayhc.supabase.co")
    hostname = url.split("//")[-1].split("/")[0]
    
    res1 = check_hostname(hostname)
    res2 = check_url(url)
    
    if res1 and res2:
        print("\n✅ All connections are working correctly!")
    else:
        print("\n❌ Connectivity issues detected. Please check your network or environment variables.")
