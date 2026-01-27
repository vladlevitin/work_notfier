# 🤖 AI-Powered Post Processing Setup

## Overview
This system uses OpenAI to automatically extract:
- **Category** (Transport, Painting, Cleaning, etc.)
- **Location** (Oslo, Asker, Viken, etc.)
- **Features** (urgency, price mentioned, contact method)

### Smart Processing
- ✅ Checks if post already exists before using AI (saves API calls)
- ✅ Only processes new or unprocessed posts
- ✅ Updates existing posts that haven't been AI-processed yet

---

## Step 1: Add Database Columns

Run this SQL in your Supabase dashboard:

1. Go to: **https://supabase.com/dashboard**
2. Select your **work_notifier** project
3. Click **SQL Editor** in the left menu
4. Click **New Query**
5. Paste this SQL:

```sql
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
```

6. Click **Run** (bottom right)
7. You should see "Success. No rows returned"

---

## Step 2: Verify Your .env File

Make sure you have OpenAI API key in your `.env`:

```
OPENAI_API_KEY=your_openai_api_key_here
```

---

## Step 3: How It Works

### When Scraping New Posts:
```python
from supabase_db import save_posts

# AI processing is automatic!
new_count, skipped_count = save_posts(scraped_posts)

# For each post:
# 1. Check if post_id exists in database
# 2. If NEW: Process with AI → Extract category, location → Save
# 3. If EXISTS + not AI-processed: Update with AI data
# 4. If EXISTS + already AI-processed: Skip (saves API calls!)
```

### AI Extraction Example:
**Input:**
```
Title: "Hei ønsker og få frakta ett dobbelt kjøleskap"
Text: "...100 til 150kg. Mortensrud"
```

**Output:**
```json
{
  "category": "Transport / Moving",
  "location": "Mortensrud, Oslo",
  "features": {
    "urgency": "normal",
    "price_mentioned": false,
    "contact_method": "pm"
  }
}
```

---

## Step 4: Test AI Processing

Run the scraper to test AI processing:

```bash
python main.py
```

You should see:
```
🤖 Processing new post with AI...
✅ AI extracted: Transport / Moving @ Oslo
```

---

## Step 5: Frontend Features

The dashboard now has:
- ✅ **Category Filter** dropdown (filters by AI-extracted category)
- ✅ **Location Filter** dropdown (filters by AI-extracted location)  
- ✅ **Category Badges** on each post (🚚, 🎨, 🧹, etc.)
- ✅ **Location Tags** on posts with extracted locations

---

## Cost Savings

**Smart Processing** saves money:
- ❌ **Old approach**: Process every post every time (wasteful!)
- ✅ **New approach**: Only process new/unprocessed posts

**Example:**
- 100 posts in database
- 5 new posts scraped
- **AI calls**: Only 5 (not 105!)

---

## Troubleshooting

### "AI processing failed"
- Check `OPENAI_API_KEY` in `.env`
- Verify OpenAI API key is valid
- Check OpenAI account has credits

### "Environment variables missing"
- Make sure `.env` file exists
- Run `python -c "from dotenv import load_dotenv; load_dotenv(); import os; print(os.getenv('OPENAI_API_KEY'))"`

### No categories showing on dashboard
- Run the SQL migration (Step 1)
- Re-scrape to process existing posts with AI
- Check browser console for errors

---

## What's Next?

Once migration is complete, all new scraped posts will automatically:
1. 🤖 Be processed by AI
2. 🏷️ Get categorized
3. 📍 Have location extracted
4. 💾 Be saved with AI data to database
5. 🎨 Display with category/location badges on dashboard

Enjoy your AI-powered job board!
