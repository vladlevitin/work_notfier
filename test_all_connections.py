"""
Comprehensive connection test for Work Notifier
Tests: Supabase DB, Local Backend, Deployed Backend
"""
import os
import requests
from dotenv import load_dotenv
from supabase import create_client, Client

# Load environment variables
load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
LOCAL_BACKEND = "http://localhost:8000"
DEPLOYED_BACKEND = "https://work-notifier-backend.onrender.com"

print("=" * 70)
print(" COMPREHENSIVE CONNECTION TEST")
print("=" * 70)

# Test 1: Supabase Direct Connection
print("\n[TEST 1] SUPABASE DATABASE CONNECTION")
print("-" * 70)
try:
    print(f"URL: {SUPABASE_URL}")
    print("Connecting to Supabase...")
    
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    response = supabase.table("posts").select("*", count="exact").execute()
    
    total = response.count
    response_new = supabase.table("posts").select("*", count="exact").eq("notified", False).execute()
    new = response_new.count
    
    print(f"[SUCCESS] Supabase connection works!")
    print(f"  - Total posts: {total}")
    print(f"  - New posts: {new}")
    print(f"  - Notified posts: {total - new}")
    
    supabase_works = True
except Exception as e:
    print(f"[FAILED] Supabase connection failed!")
    print(f"  Error: {str(e)}")
    supabase_works = False

# Test 2: Local Backend
print("\n[TEST 2] LOCAL BACKEND API (localhost:8000)")
print("-" * 70)
try:
    print(f"URL: {LOCAL_BACKEND}/api/stats")
    print("Connecting to local backend...")
    
    response = requests.get(f"{LOCAL_BACKEND}/api/stats", timeout=10)
    
    if response.status_code == 200:
        data = response.json()
        print(f"[SUCCESS] Local backend works!")
        print(f"  - Status Code: {response.status_code}")
        print(f"  - Response: {data}")
        local_works = True
    else:
        print(f"[FAILED] Local backend returned error!")
        print(f"  - Status Code: {response.status_code}")
        print(f"  - Response: {response.text[:200]}")
        local_works = False
        
except requests.exceptions.ConnectionError:
    print(f"[NOT RUNNING] Local backend is not running")
    print(f"  This is OK if you're not testing locally")
    local_works = False
except Exception as e:
    print(f"[FAILED] Local backend error!")
    print(f"  Error: {str(e)}")
    local_works = False

# Test 3: Deployed Backend
print("\n[TEST 3] DEPLOYED BACKEND API (Render)")
print("-" * 70)
try:
    print(f"URL: {DEPLOYED_BACKEND}/api/stats")
    print("Connecting to deployed backend...")
    print("(This may take 30-60 seconds if service is sleeping...)")
    
    response = requests.get(f"{DEPLOYED_BACKEND}/api/stats", timeout=120)
    
    if response.status_code == 200:
        data = response.json()
        print(f"[SUCCESS] Deployed backend works!")
        print(f"  - Status Code: {response.status_code}")
        print(f"  - Response: {data}")
        deployed_works = True
    else:
        print(f"[FAILED] Deployed backend returned error!")
        print(f"  - Status Code: {response.status_code}")
        print(f"  - Response: {response.text[:500]}")
        deployed_works = False
        
except requests.exceptions.Timeout:
    print(f"[TIMEOUT] Deployed backend took too long to respond")
    print(f"  Possible causes:")
    print(f"    1. Service is sleeping and didn't wake up in 120s")
    print(f"    2. Deployment has errors")
    print(f"    3. Missing environment variables")
    deployed_works = False
except requests.exceptions.ConnectionError as e:
    print(f"[FAILED] Cannot connect to deployed backend")
    print(f"  Error: {str(e)}")
    print(f"  Possible causes:")
    print(f"    1. Backend not deployed")
    print(f"    2. Wrong URL")
    print(f"    3. Service suspended")
    deployed_works = False
except Exception as e:
    print(f"[FAILED] Deployed backend error!")
    print(f"  Error: {str(e)}")
    deployed_works = False

# Summary
print("\n" + "=" * 70)
print(" TEST SUMMARY")
print("=" * 70)

results = [
    ("Supabase Database", supabase_works),
    ("Local Backend (localhost:8000)", local_works),
    ("Deployed Backend (Render)", deployed_works)
]

for name, status in results:
    status_text = "[OK]    " if status else "[FAILED]"
    print(f"{status_text} {name}")

print("\n" + "=" * 70)
print(" DIAGNOSIS")
print("=" * 70)

if supabase_works and not deployed_works:
    print("\n[ISSUE IDENTIFIED] Deployed backend cannot connect to Supabase")
    print("\nMost likely cause: Missing environment variables on Render")
    print("\nFIX:")
    print("1. Go to: https://dashboard.render.com/")
    print("2. Click on 'work-notifier-backend'")
    print("3. Click 'Environment' tab")
    print("4. Add these 3 variables:")
    print(f"\n   SUPABASE_URL = {SUPABASE_URL}")
    print(f"   SUPABASE_KEY = {SUPABASE_KEY}")
    print(f"   SUPABASE_SERVICE_KEY = {os.getenv('SUPABASE_SERVICE_KEY')}")
    print("\n5. Click 'Save Changes' (auto-redeploys)")
    print("6. Wait 2-3 minutes for redeploy")
    print("7. Re-run this test")

elif not supabase_works:
    print("\n[ISSUE IDENTIFIED] Supabase database is not accessible")
    print("\nFIX:")
    print("1. Check if Supabase project is paused")
    print("2. Verify API keys are correct")
    print("3. Check if 'posts' table exists")

elif supabase_works and deployed_works:
    print("\n[ALL SYSTEMS GO!]")
    print("\nEverything is working! Now configure Vercel:")
    print("\n1. Go to: https://vercel.com/dashboard")
    print("2. Click your project")
    print("3. Settings -> Environment Variables")
    print("4. Add:")
    print(f"\n   VITE_API_URL = {DEPLOYED_BACKEND}")
    print("\n5. Deployments -> Redeploy")
    print("\nDone! Your dashboard will work on Vercel!")

print("\n" + "=" * 70)
