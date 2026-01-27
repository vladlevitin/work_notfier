# 🗄️ **Database Migration - Run This SQL**

## ⚡ Quick Setup (2 Minutes)

### **Step 1: Open Supabase SQL Editor**
👉 **Click here:** https://supabase.com/dashboard/project/ipfghgunlexexcdlhrpr/sql/new

### **Step 2: Copy & Paste This SQL**

```sql
-- ============================================================
-- Add posted_at column for proper date sorting
-- ============================================================
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS posted_at TIMESTAMP WITH TIME ZONE;

-- Create index for fast sorting by posted date
CREATE INDEX IF NOT EXISTS idx_posts_posted_at ON posts(posted_at DESC);

-- Migrate existing posts: use scraped_at as posted_at
UPDATE posts 
SET posted_at = scraped_at 
WHERE posted_at IS NULL;

-- ============================================================
-- Add AI processing columns
-- ============================================================
ALTER TABLE posts 
ADD COLUMN IF NOT EXISTS category TEXT,
ADD COLUMN IF NOT EXISTS location TEXT,
ADD COLUMN IF NOT EXISTS ai_processed BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS ai_features JSONB;

-- Create indexes for fast filtering
CREATE INDEX IF NOT EXISTS idx_posts_category ON posts(category);
CREATE INDEX IF NOT EXISTS idx_posts_location ON posts(location);
CREATE INDEX IF NOT EXISTS idx_posts_ai_processed ON posts(ai_processed);

-- ============================================================
-- Done! ✅
-- ============================================================
```

### **Step 3: Click "Run" (bottom right)**

You should see: ✅ **"Success. No rows returned"**

### **Step 4: I'll Update the API**

After you run the SQL, I'll update the API to sort by `posted_at` properly.

---

## 🎯 **What This Does**

- ✅ Adds `posted_at` column - sorts posts by actual Facebook posting time
- ✅ Adds AI columns - enables category/location extraction
- ✅ Creates indexes - makes queries fast
- ✅ Migrates old posts - sets posted_at = scraped_at for existing posts

---

## ✨ **After Running SQL**

Your posts will be sorted correctly:
- "7h" ago posts at TOP ⬆️
- "8h" ago posts next
- "10h" ago posts after
- Older posts at BOTTOM ⬇️

---

**Run the SQL now, then tell me when done!** 🚀
