# 🗄️ Database Migration Guide

## Required Migrations

You need to run **2 SQL migrations** in your Supabase dashboard to enable all new features:

### Migration 1: AI Processing Columns
### Migration 2: Posted At Timestamp

---

## How to Run Migrations

1. Go to: **https://supabase.com/dashboard/project/ipfghgunlexexcdlhrpr/sql**
2. Click **"New Query"**
3. Copy and paste **BOTH** SQL blocks below
4. Click **"Run"** (bottom right)
5. You should see "Success. No rows returned"

---

## SQL Migration (Copy & Paste This)

```sql
-- ============================================================
-- MIGRATION 1: Add AI Processing Columns
-- ============================================================

-- Add AI processing columns to posts table
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS category TEXT,
ADD COLUMN IF NOT EXISTS location TEXT,
ADD COLUMN IF NOT EXISTS ai_processed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS ai_features JSONB;

-- Create indexes for faster filtering
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_location ON posts(location);
CREATE INDEX IF NOT EXISTS idx_posts_ai_processed ON posts(ai_processed);

-- ============================================================
-- MIGRATION 2: Add Posted At Timestamp for Proper Sorting
-- ============================================================

-- Add posted_at timestamp column
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP WITH TIME ZONE;

-- Create index for faster sorting
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at DESC);

-- Migrate existing data: set posted_at to scraped_at for old posts
UPDATE posts 
SET posted_at = scraped_at 
WHERE posted_at IS NULL;

-- ============================================================
-- Done! 🎉
-- ============================================================
```

---

## What These Columns Do

### AI Processing Columns:
- **category** - AI-extracted job category (Transport, Painting, Cleaning, etc.)
- **location** - AI-extracted location (Oslo, Asker, etc.)
- **ai_processed** - Prevents re-processing posts (saves API costs)
- **ai_features** - Additional AI insights (urgency, price, contact method)

### Sorting Column:
- **posted_at** - Proper timestamp for when post was made on Facebook
  - Parses Facebook formats: "7h", "24 January at 08:42", etc.
  - Enables sorting by actual posting time (not scrape time)

---

## Features Enabled After Migration

✅ **Category Filter** - Filter posts by job type  
✅ **Location Filter** - Filter posts by area  
✅ **Proper Sorting** - Newest posted jobs first (not newest scraped)  
✅ **Category Badges** - Visual tags on each post  
✅ **Location Tags** - Shows where job is located  
✅ **Smart AI Processing** - Only processes new posts (saves money)

---

## After Running Migration

1. ✅ Vercel is deploying updated backend
2. ✅ Frontend will show category/location filters
3. ✅ Posts will be sorted by posted date (latest first)
4. ⏳ Next scrape will auto-process posts with AI

Refresh your dashboard to see the changes: **https://work-notfier.vercel.app**

---

## Troubleshooting

**"column already exists" error?**  
→ That's fine! The migration uses `IF NOT EXISTS` so it's safe to run multiple times

**No categories showing yet?**  
→ Run a new scrape (`python main.py`) to process existing posts with AI

**Posts not sorted correctly?**  
→ Old posts will use scraped_at for sorting. New posts will use posted_at

**Need to re-process all posts with AI?**  
→ Run: `UPDATE posts SET ai_processed = FALSE;` then re-scrape
