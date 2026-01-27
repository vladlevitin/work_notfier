"""Run database migration using Supabase REST API."""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")

print("Running database migration...")
print(f"Supabase URL: {SUPABASE_URL}")

# SQL statements to execute
sql_statements = [
    "ALTER TABLE posts ADD COLUMN IF NOT EXISTS category TEXT",
    "ALTER TABLE posts ADD COLUMN IF NOT EXISTS location TEXT",
    "ALTER TABLE posts ADD COLUMN IF NOT EXISTS ai_processed BOOLEAN DEFAULT FALSE",
    "ALTER TABLE posts ADD COLUMN IF NOT EXISTS ai_features JSONB"
]

# Note: Supabase doesn't allow direct SQL execution via REST API for security
# These columns need to be added via Supabase Dashboard > SQL Editor
# OR using the Supabase CLI with migrations

print("\n[INFO] Execute this SQL in Supabase Dashboard > SQL Editor:")
print("\n" + open("add_ai_columns.sql").read())
print("\nOR run: supabase migration new add_ai_columns")
print("Then copy the SQL into the migration file and run: supabase db push")
