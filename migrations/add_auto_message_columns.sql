-- Add auto-message tracking columns to posts table

ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS auto_message_sent BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS auto_message_text TEXT,
ADD COLUMN IF NOT EXISTS auto_message_price_nok INTEGER,
ADD COLUMN IF NOT EXISTS auto_message_hours REAL,
ADD COLUMN IF NOT EXISTS auto_message_item_summary TEXT,
ADD COLUMN IF NOT EXISTS auto_message_sent_at TIMESTAMPTZ;

-- Create index for faster filtering of messaged posts
CREATE INDEX IF NOT EXISTS idx_posts_auto_message_sent ON posts(auto_message_sent);

-- Add comments
COMMENT ON COLUMN posts.auto_message_sent IS 'Whether an auto-DM was sent to the poster';
COMMENT ON COLUMN posts.auto_message_text IS 'The auto-generated message text that was sent';
COMMENT ON COLUMN posts.auto_message_price_nok IS 'Estimated price in NOK that was quoted';
COMMENT ON COLUMN posts.auto_message_hours IS 'Estimated hours for the job';
COMMENT ON COLUMN posts.auto_message_item_summary IS 'Brief description of items to move';
COMMENT ON COLUMN posts.auto_message_sent_at IS 'When the auto-message was sent';
