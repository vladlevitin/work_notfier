-- Supabase Database Schema for Facebook Work Notifier
-- Run this in your Supabase SQL Editor

-- Create posts table
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

-- Create policy to allow all operations (adjust as needed)
CREATE POLICY "Allow all operations on posts" ON posts
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Create storage bucket for posts (optional, for future use)
-- This is done via Supabase Dashboard -> Storage -> Create bucket
-- Bucket name: work_notifier
-- Public: false
