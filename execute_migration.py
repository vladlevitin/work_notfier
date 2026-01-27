"""Execute database migration by adding columns manually via Supabase client."""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Executing database migration...")
print("Note: This uses the Supabase PostgREST API which may have limitations")
print()

# Since Supabase Python client doesn't support raw SQL execution,
# we need to use the SQL Editor in the dashboard OR use psycopg2

print("[INFO] The SQL migration needs to be run in Supabase SQL Editor.")
print()
print("Copy this SQL and run it at:")
print(f"https://supabase.com/dashboard/project/{SUPABASE_URL.split('//')[1].split('.')[0]}/sql/new")
print()
print("="*70)
with open("add_ai_columns.sql", "r") as f:
    print(f.read())
print("="*70)
print()
print("After running the SQL, press Enter to continue...")
input()

print("\n[OK] Proceeding with AI processing test...")
print()

# Test: Try to get posts and see if new columns exist
try:
    result = supabase.table("posts").select("post_id, category, location, ai_processed").limit(1).execute()
    if result.data:
        print("[SUCCESS] Migration successful! New columns are accessible.")
        print(f"Sample data: {result.data[0]}")
    else:
        print("[INFO] No posts in database yet to test columns.")
except Exception as e:
    print(f"[ERROR] Migration may not be complete: {e}")
    print("Please run the SQL in Supabase dashboard and try again.")
