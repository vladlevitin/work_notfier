-- Add AI processing columns to posts table

ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS category TEXT,
ADD COLUMN IF NOT EXISTS secondary_categories TEXT,
ADD COLUMN IF NOT EXISTS location TEXT,
ADD COLUMN IF NOT EXISTS ai_processed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS ai_features JSONB;

-- Create index for faster filtering
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_location ON posts(location);
CREATE INDEX IF NOT EXISTS idx_posts_ai_processed ON posts(ai_processed);

-- Add comment
COMMENT ON COLUMN posts.category IS 'AI-extracted category (e.g., Transport, Painting, etc.)';
COMMENT ON COLUMN posts.location IS 'AI-extracted location from post content';
COMMENT ON COLUMN posts.ai_processed IS 'Whether this post has been processed by AI';
COMMENT ON COLUMN posts.ai_features IS 'Additional AI-extracted features as JSON';
