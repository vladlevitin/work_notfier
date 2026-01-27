"""Final attempt: Create table using Supabase connection pooler."""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_PASSWORD = "fhKgKeDm0YUnxd7Y"
PROJECT_ID = "ipfghgunlexexcdlhrpr"

# Try different connection methods
CONNECTION_ATTEMPTS = [
    f"postgresql://postgres.{PROJECT_ID}:{DB_PASSWORD}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres",
    f"postgresql://postgres:{DB_PASSWORD}@aws-0-eu-central-1.pooler.supabase.com:6543/postgres?options=project%3D{PROJECT_ID}",
]

SQL = """
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

CREATE INDEX IF NOT EXISTS idx_posts_post_id ON posts(post_id);
CREATE INDEX IF NOT EXISTS idx_posts_group_url ON posts(group_url);
CREATE INDEX IF NOT EXISTS idx_posts_notified ON posts(notified);

ALTER TABLE posts ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all operations on posts" ON posts;
CREATE POLICY "Allow all operations on posts" ON posts FOR ALL USING (true) WITH CHECK (true);
"""

print("="*80)
print("ATTEMPTING REMOTE DATABASE TABLE CREATION")
print("="*80)

for i, conn_str in enumerate(CONNECTION_ATTEMPTS, 1):
    print(f"\nAttempt {i}...")
    try:
        conn = psycopg2.connect(conn_str, connect_timeout=10)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("  Connected successfully!")
        print("  Executing SQL...")
        
        cursor.execute(SQL)
        
        print("  SUCCESS! Table created!")
        
        cursor.execute("SELECT COUNT(*) FROM posts;")
        count = cursor.fetchone()[0]
        print(f"  Verified: posts table exists with {count} rows")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*80)
        print("SETUP COMPLETE!")
        print("="*80)
        print("Refresh your dashboard - it should now work!")
        exit(0)
        
    except Exception as e:
        print(f"  Failed: {e}")
        continue

print("\n" + "="*80)
print("ALL CONNECTION ATTEMPTS FAILED")
print("="*80)
print("\nI cannot create the table remotely because:")
print("1. Supabase requires dashboard login for SQL execution")
print("2. Database connection requires network access I don't have")
print("\nYou MUST manually run the SQL in Supabase:")
print("https://supabase.com/dashboard/project/ipfghgunlexexcdlhrpr/sql/new")
print("\nIt takes 30 seconds - just copy the SQL from supabase_schema.sql and click Run")
