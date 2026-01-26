# Deployment Verification Checklist

## 🔍 Step 1: Check Backend Deployment

### Find Your Backend URL
- Go to your Render/Railway dashboard
- Find the "work_notifier" or "work-notifier-backend" service
- Copy the URL (e.g., `https://work-notifier-backend.onrender.com`)

### Test Backend Health
Open these URLs in your browser or run:

```bash
# Health check
curl https://YOUR-BACKEND-URL.onrender.com/health

# Should return: {"status":"healthy"}

# Stats endpoint
curl https://YOUR-BACKEND-URL.onrender.com/api/stats

# Should return: {"total":16,"new":10,"by_group":[...]}

# Posts endpoint  
curl https://YOUR-BACKEND-URL.onrender.com/api/posts?limit=5

# Should return: {"posts":[...],"total":16,"limit":5,"offset":0}
```

---

## ⚙️ Step 2: Verify Backend Environment Variables

Go to your backend deployment platform and check these environment variables are set:

### Required Variables:
```
SUPABASE_URL=https://ipfghgunlexexcdlhrpr.supabase.co

SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNTYwMTQsImV4cCI6MjA4NDkzMjAxNH0.YlIEHih0-K_JC-Bak3JHTicLYA2exRS_V2hKfOzH0qM

SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTM1NjAxNCwiZXhwIjoyMDg0OTMyMDE0fQ.9gT1bKQ7080rb3-Gu6aTrT17FvmOK4kmptDV4BSBp9c
```

### How to Add (Render):
1. Go to your service dashboard
2. Click **"Environment"** tab
3. Click **"Add Environment Variable"**
4. Add each variable above

### How to Add (Railway):
1. Go to your project
2. Click **"Variables"** tab
3. Click **"New Variable"**
4. Add each variable above

---

## 🎨 Step 3: Verify Frontend Configuration

Go to your Vercel dashboard and check:

### Environment Variable Required:
```
VITE_API_URL=https://YOUR-BACKEND-URL.onrender.com
```

Replace `YOUR-BACKEND-URL.onrender.com` with your actual backend URL from Step 1.

### How to Add (Vercel):
1. Go to your project dashboard
2. Click **"Settings"**
3. Click **"Environment Variables"**
4. Add:
   - **Name**: `VITE_API_URL`
   - **Value**: Your backend URL
   - **Environment**: Production, Preview, Development (check all)
5. Click **"Save"**
6. Go to **"Deployments"** tab
7. Click **"..."** on the latest deployment
8. Click **"Redeploy"**

---

## 🚨 Common Issues

### Issue 1: "Failed to fetch posts"
**Cause**: Frontend can't connect to backend
**Fix**: 
- Verify `VITE_API_URL` is set in Vercel
- Verify backend is running and healthy
- Check CORS is enabled (already done in code)

### Issue 2: Backend returns 500 error
**Cause**: Environment variables not set
**Fix**: Add all 3 Supabase variables to backend platform

### Issue 3: Backend shows "healthy" but no data
**Cause**: Wrong Supabase keys or table doesn't exist
**Fix**: 
- Verify keys in environment variables match your .env
- Check Supabase SQL Editor that `posts` table exists

---

## ✅ If Everything Works

You should see:
- Backend `/health`: `{"status":"healthy"}`
- Backend `/api/stats`: Shows your 16 posts
- Frontend dashboard: Displays all 16 posts with stats

---

## 🆘 Quick Debug Commands

```bash
# Get backend URL from Vercel
vercel env ls

# Test backend from command line
curl -v https://YOUR-BACKEND-URL/api/stats

# Check backend logs
# Go to Render/Railway dashboard → Logs tab
```

---

## 📞 Still Not Working?

1. Check deployment logs on Render/Railway for errors
2. Check browser console (F12) for error messages
3. Verify all environment variables are exactly as shown (no extra spaces)
4. Try redeploying both backend and frontend after setting variables
