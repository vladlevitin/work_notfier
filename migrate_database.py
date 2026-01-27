"""Run database migration to add AI processing columns."""

import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=" * 70)
print(" DATABASE MIGRATION: Adding AI Processing Columns")
print("=" * 70)

# Read SQL migration file
with open("add_ai_columns.sql", "r") as f:
    sql = f.read()

print("\nSQL Migration:")
print(sql)
print("\n" + "=" * 70)

try:
    # Execute SQL directly using Supabase's RPC or PostgreSQL client
    # Note: Supabase Python client doesn't have direct SQL execution
    # You need to run this SQL manually in Supabase dashboard SQL editor
    # OR use postgrest / psycopg2 for direct PostgreSQL connection
    
    print("\n[!] MANUAL MIGRATION REQUIRED")
    print("\nPlease run the SQL above in your Supabase dashboard:")
    print("1. Go to: https://supabase.com/dashboard")
    print("2. Select your 'work_notifier' project")
    print("3. Click 'SQL Editor' in the left menu")
    print("4. Paste the SQL from 'add_ai_columns.sql'")
    print("5. Click 'Run'")
    print("\nOR use the Supabase CLI:")
    print("  supabase db push")
    
    print("\n" + "=" * 70)
    print(" Migration script created: add_ai_columns.sql")
    print("=" * 70)
    
except Exception as e:
    print(f"\n[X] Error: {e}")
