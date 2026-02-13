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

# Read migration SQL files
with open("migrations/add_posted_at_column.sql", "r") as f:
    posted_at_sql = f.read()

with open("migrations/add_ai_columns.sql", "r") as f:
    ai_sql = f.read()

with open("migrations/add_auto_message_columns.sql", "r") as f:
    auto_msg_sql = f.read()

print("\nMigrations to run:")
print("  1. AI columns (category, location, etc.)")
print("  2. posted_at column")
print("  3. Auto-message columns (auto_message_sent, price, hours, etc.)")

# Print all SQL for user to run in Supabase
try:
    print("\nIMPORTANT: Please run this SQL in Supabase SQL Editor:")
    print("https://supabase.com/dashboard/project/ipfghgunlexexcdlhrpr/sql/new")
    print("\n" + "="*70)
    print("-- Migration 1: AI columns")
    print(ai_sql)
    print("\n-- Migration 2: posted_at column")
    print(posted_at_sql)
    print("\n-- Migration 3: Auto-message columns")
    print(auto_msg_sql)
    print("="*70)
    
    input("\nPress Enter after running the SQL in Supabase...")
    
    # Verify columns exist
    result = supabase.table("posts").select("category, location, posted_at, auto_message_sent").limit(1).execute()
    print("\n[OK] Migration successful! All columns are accessible.")
    print(f"Sample: {result.data[0] if result.data else 'No posts yet'}")
    
except Exception as e:
    print(f"\n[ERROR] {e}")
    print("\nPlease run the SQL manually in Supabase dashboard.")
