"""Create database tables in Supabase for Facebook Work Notifier.

Run this script once to set up the database schema.
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get Supabase credentials
SUPABASE_URL = os.getenv("SUPABASE_URL")
SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SECRET_KEY")

if not SUPABASE_URL or not SERVICE_KEY:
    print("ERROR: SUPABASE_URL and SUPABASE_SERVICE_KEY must be set in .env file")
    sys.exit(1)

# Extract database connection info from Supabase URL
# Format: https://PROJECT_ID.supabase.co
project_id = SUPABASE_URL.replace("https://", "").replace(".supabase.co", "")

print("="*80)
print("DATABASE TABLE SETUP")
print("="*80)
print(f"Supabase Project: {project_id}")
print("\nYou need to manually create the table in Supabase SQL Editor.")
print("\nFollow these steps:")
print("\n1. Open this URL in your browser:")
print(f"   https://supabase.com/dashboard/project/{project_id}/sql/new")
print("\n2. Copy and paste the SQL below into the editor:")
print("="*80)

SQL_SCHEMA = """-- Create posts table
CREATE TABLE IF NOT EXISTS posts (
    id BIGSERIAL PRIMARY KEY,
    post_id TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    url TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    group_name TEXT NOT NULL,
    group_url TEXT NOT NULL,
    scraped_at TIMESTAMPTZ DEFAULT NOW(),
    notified BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id);
CREATE INDEX IF NOT EXISTS idx_posts_group_url ON posts(group_url);
CREATE INDEX IF NOT EXISTS idx_posts_scraped_at ON posts(scraped_at DESC);
CREATE INDEX IF NOT EXISTS idx_posts_notified ON posts(notified);
CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create trigger to automatically update updated_at
DROP TRIGGER IF EXISTS update_posts_updated_at ON posts;
CREATE TRIGGER update_posts_updated_at
    BEFORE UPDATE ON posts
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Enable Row Level Security (RLS)
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

-- Create policy to allow all operations
DROP POLICY IF EXISTS "Allow all operations on posts" ON posts;
CREATE POLICY "Allow all operations on posts" ON posts
    FOR ALL
    USING (true)
    WITH CHECK (true);"""

print(SQL_SCHEMA)
print("\n" + "="*80)
print("\n3. Click the 'Run' button (or press F5)")
print("\n4. You should see: 'Success. No rows returned'")
print("\n5. Then run: python main.py")
print("="*80)

# Test connection after user confirms
input("\nPress Enter after you've run the SQL in Supabase...")

print("\nTesting database connection...")
try:
    from supabase_db import supabase
    result = supabase.table("posts").select("id", count="exact").limit(1).execute()
    print(f"SUCCESS! Database connected. Total posts: {result.count if result.count else 0}")
    print("\nYou can now run: python main.py")
except Exception as e:
    print(f"ERROR: Could not connect to database: {e}")
    print("\nMake sure you ran the SQL in Supabase SQL Editor!")
    sys.exit(1)
