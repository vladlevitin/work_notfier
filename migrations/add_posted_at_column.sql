-- Add posted_at timestamp column for proper sorting
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP WITH TIME ZONE;

-- Create index for faster sorting
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at DESC);

-- Migrate existing data: set posted_at to scraped_at for old posts
-- (We don't have exact posting time for old posts)
UPDATE posts 
SET posted_at = scraped_at 
WHERE posted_at IS NULL;
