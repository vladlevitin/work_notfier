"""Run database migration to add posted_at and AI columns."""

import os
import sys
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from database.supabase_db import supabase

load_dotenv()

print("="*70)
print(" Running Database Migration")
print("="*70)

# Read migration SQL
with open("migrations/add_posted_at_column.sql", "r") as f:
    posted_at_sql = f.read()

with open("migrations/add_ai_columns.sql", "r") as f:
    ai_sql = f.read()

print("\n[1/2] Adding AI columns...")
print(ai_sql[:200] + "...\n")

# Execute AI columns migration
try:
    # Supabase Python client doesn't support raw SQL, so we'll use RPC
    # Instead, we'll print instructions
    print("IMPORTANT: Please run this SQL in Supabase SQL Editor:")
    print("https://supabase.com/dashboard/project/ipfghgunlexexcdlhrpr/sql/new")
    print("\n" + "="*70)
    print(ai_sql)
    print("="*70)
    print("\n" + "="*70)
    print(posted_at_sql)
    print("="*70)
    
    input("\nPress Enter after running the SQL in Supabase...")
    
    # Verify columns exist
    result = supabase.table("posts").select("category, location, posted_at").limit(1).execute()
    print("\n✅ Migration successful! Columns are accessible.")
    print(f"Sample: {result.data[0] if result.data else 'No posts yet'}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    print("\nPlease run the SQL manually in Supabase dashboard.")
