# 🚀 Supabase Setup Instructions

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

## Step 2: Run Database Schema

1. In your Supabase dashboard, go to **SQL Editor** (left sidebar)
2. Click "New query"
3. Copy the entire contents of `supabase_schema.sql`
4. Paste into the SQL editor
5. Click **"Run"** or press `Ctrl+Enter`
6. You should see: ✅ "Success. No rows returned"

---

## Step 3: Get API Credentials

### Get Supabase URL and Key:

1. In Supabase dashboard, click **Settings** (⚙️ icon at bottom left)
2. Go to **API** section
3. Copy these values:

   **Project URL:**
   ```
   https://xxxxx.supabase.co
   ```

   **anon/public key:**
   ```
   eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3M...
   ```

---

## Step 4: Update .env File

Edit your `.env` file and add Supabase credentials:

```env
# Microsoft Graph API (for email notifications)
TENANT_ID=your_tenant_id
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SENDER_EMAIL=your_email@example.com

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=eyJhbGci...your_key_here
```

---

## Step 5: (Optional) Create Storage Bucket

If you want to store files/images in the future:

1. In Supabase dashboard, go to **Storage**
2. Click "New bucket"
3. Name: `work_notifier`
4. Set as **Private** (uncheck "Public bucket")
5. Click "Create bucket"

---

## Step 6: Test Connection

Run this to test your Supabase connection:

```bash
python supabase_db.py
```

You should see:
```
Connecting to Supabase at https://xxxxx.supabase.co
✅ Successfully connected to Supabase!
Total posts in database: 0
```

---

## Step 7: Deploy Backend to Render

### Option A: Render Dashboard

1. Go to [render.com](https://render.com)
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Settings:
   - **Name**: `work-notifier-api`
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r ../requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variables:
   - `SUPABASE_URL`: (from Step 3)
   - `SUPABASE_KEY`: (from Step 3)
6. Click "Create Web Service"

---

## Step 8: Update Frontend API URL

Once your backend is deployed, update the frontend to use it:

Edit `frontend/src/api/client.ts`:

```typescript
const API_BASE = 'https://your-backend-url.onrender.com/api';
// or keep '/api' for local development
```

Or add environment variable in Vercel:
- Variable: `VITE_API_URL`
- Value: `https://your-backend-url.onrender.com/api`

---

## Troubleshooting

### "Failed to connect to Supabase"
- Check that `SUPABASE_URL` and `SUPABASE_KEY` are correct in `.env`
- Make sure you're using the **anon/public** key, not the service_role key
- Verify you ran the SQL schema

### "Posts not showing in dashboard"
- Make sure backend is deployed and running
- Check backend logs in Render dashboard
- Verify CORS is enabled in backend (it already is)

### "Email not sending"
- Verify Microsoft Graph API credentials in `.env`
- Check that you have the correct permissions in Azure AD

---

## What's Different from SQLite?

### Advantages of Supabase:
✅ **Cloud-hosted** - Access from anywhere  
✅ **Real-time** - Dashboard updates automatically  
✅ **Scalable** - Handles many posts/users  
✅ **Backups** - Automatic daily backups  
✅ **Web UI** - Browse data in Supabase dashboard  

### Migration from SQLite:
- Old SQLite file: `facebook_posts.db` (can delete)
- New Supabase: All data stored in cloud
- Same API/functionality, just different backend

---

## Database Structure

The `posts` table stores:
- `post_id` - Unique identifier from Facebook
- `title` - First line of post
- `text` - Full post content
- `url` - Link to Facebook post
- `timestamp` - When posted on Facebook
- `group_name` - Name of Facebook group
- `group_url` - URL of Facebook group
- `scraped_at` - When added to database
- `notified` - Whether email was sent

---

**You're all set!** 🎉 Run `python main.py` to start scraping and uploading to Supabase!
