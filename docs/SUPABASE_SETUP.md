# 🚀 Supabase Setup Instructions (SQLAlchemy + PostgreSQL)

## Overview

This setup uses **SQLAlchemy with Supabase PostgreSQL** (same as Tinder automation), NOT the Supabase Python SDK.

---

## Step 1: Create Supabase Project

1. Go to [supabase.com](https://supabase.com)
2. Sign in / Create account
3. Click "New Project"
4. Fill in:
   - **Name**: `work-notifier`
   - **Database Password**: (save this!)
   - **Region**: Choose closest to you
5. Click "Create new project" and wait 2-3 minutes

---

## Step 2: Get PostgreSQL Connection String

1. In your Supabase dashboard, go to **Settings** (⚙️ icon at bottom left)
2. Go to **Database** section
3. Scroll down to **Connection string** → **URI**
4. Copy the connection string:

   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

5. **Replace `[YOUR-PASSWORD]`** with your actual database password from Step 1

---

## Step 3: Run Database Schema

1. In your Supabase dashboard, go to **SQL Editor** (left sidebar)
2. Click "New query"
3. Copy the entire contents of `supabase_schema.sql`
4. Paste into the SQL editor
5. Click **"Run"** or press `Ctrl+Enter`
6. You should see: ✅ "Success. No rows returned"

---

## Step 4: Update .env File

Edit your `.env` file and add the PostgreSQL connection string:

```env
# Microsoft Graph API (for email notifications)
TENANT_ID=your_tenant_id
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SENDER_EMAIL=your_email@example.com

# Supabase PostgreSQL Database
DATABASE_URL=postgresql://postgres:your_password@db.xxxxx.supabase.co:5432/postgres
```

---

## Step 5: Install Dependencies

```bash
pip install sqlalchemy psycopg2-binary
```

---

## Step 6: Test Connection

Run this to test your database connection:

```bash
python database_sqlalchemy.py
```

You should see:
```
✅ Database schema initialized
✅ Successfully connected to database!
Total posts in database: 0
```

---

## Step 7: Run the Scraper

```bash
python main.py
```

This will:
- Connect to Supabase PostgreSQL
- Show database stats
- Scrape Facebook groups
- Save ALL posts to database
- Send email for NEW relevant posts

---

## Architecture (Same as Tinder Automation)

```
┌─────────────────┐
│  main.py        │  Scraper script
│  (Python)       │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  SQLAlchemy     │  Database ORM
│  (Python)       │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│  PostgreSQL     │  Supabase hosted
│  (Supabase)     │
└─────────────────┘
```

**Key Points:**
- ✅ Uses **SQLAlchemy** (same as Tinder automation)
- ✅ Connects via **PostgreSQL connection string**
- ✅ No Supabase Python SDK needed for data
- ✅ Standard SQL operations

---

## Troubleshooting

### "Failed to connect to database"
- Check that `DATABASE_URL` is correct in `.env`
- Make sure you replaced `[YOUR-PASSWORD]` with actual password
- Verify Supabase project is active

### "relation 'posts' does not exist"
- Run the SQL schema in Supabase SQL Editor
- Check that the schema ran successfully

### "No module named 'psycopg2'"
- Install: `pip install psycopg2-binary`

---

## What's Different from Previous Version?

### Before (Supabase SDK):
```python
from supabase import create_client
supabase = create_client(url, key)
supabase.table("posts").insert(...)
```

### Now (SQLAlchemy - Same as Tinder):
```python
from sqlalchemy import create_engine
engine = create_engine(DATABASE_URL)
db.add(PostModel(...))
db.commit()
```

**Why?**
- ✅ Matches Tinder automation pattern
- ✅ More flexible and powerful
- ✅ Better for complex queries
- ✅ Industry standard ORM

---

**You're all set!** 🎉 Run `python main.py` to start scraping!
