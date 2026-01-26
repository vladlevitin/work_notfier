# 🔧 Quick Fix for Vercel Deployment

## Problem: Localhost works, Vercel doesn't fetch data

## Solution: 2 Options

---

## Option A: You Already Have Backend Deployed

### Step 1: Find Your Backend URL
1. Go to your backend platform (Render/Railway/etc.)
2. Copy the backend URL (e.g., `https://work-notifier-backend.onrender.com`)

### Step 2: Configure Vercel
1. Go to: https://vercel.com/dashboard
2. Click on your project
3. Go to **Settings** → **Environment Variables**
4. Add new variable:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://your-backend-url.onrender.com` (your actual backend URL)
   - **Environments**: Check all three (Production, Preview, Development)
5. Click **Save**

### Step 3: Redeploy
1. Go to **Deployments** tab
2. Click "..." on the latest deployment
3. Click **"Redeploy"**
4. Wait 1-2 minutes
5. ✅ Done! Your Vercel dashboard will now fetch from Supabase via the backend!

---

## Option B: No Backend Yet - Deploy Now (10 minutes)

### Step 1: Deploy Backend to Render

#### 1.1 Sign Up
Go to: https://dashboard.render.com/register
Sign up with GitHub

#### 1.2 Create Web Service
1. Click **"New +"** → **"Web Service"**
2. Connect repository: `vladlevitin/work_notfier`
3. Configure:
   ```
   Name: work-notifier-backend
   Region: Frankfurt (EU Central)
   Branch: main
   Root Directory: backend
   Runtime: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
   Instance Type: Free
   ```

#### 1.3 Add Environment Variables
Click **"Advanced"** → Add these 3 variables:

**Variable 1:**
```
SUPABASE_URL
https://ipfghgunlexexcdlhrpr.supabase.co
```

**Variable 2:**
```
SUPABASE_KEY
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocHByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNTYwMTQsImV4cCI6MjA4NDkzMjAxNH0.YlIEHih0-K_JC-Bak3JHTicLYA2exRS_V2hKfOzH0qM
```

**Variable 3:**
```
SUPABASE_SERVICE_KEY
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocHByIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTM1NjAxNCwiZXhwIjoyMDg0OTMyMDE0fQ.9gT1bKQ7080rb3-Gu6aTrT17FvmOK4kmptDV4BSBp9c
```

#### 1.4 Deploy
1. Click **"Create Web Service"**
2. Wait 2-3 minutes
3. **COPY THE URL** (e.g., `https://work-notifier-backend.onrender.com`)

#### 1.5 Test Backend
Open: `https://your-backend-url.onrender.com/api/stats`
Should show: `{"total":16,"new":10,...}`

### Step 2: Configure Vercel (Same as Option A)
Follow Option A Steps 2 & 3 above using the backend URL you just got.

---

## ✅ How to Verify It Works

### Test 1: Backend Direct
Open: `https://your-backend-url.onrender.com/api/stats`
Should see your 16 posts

### Test 2: Vercel Dashboard
Open: `https://your-project.vercel.app`
Should see:
- Total Posts: 16
- New Posts: 10
- All posts displayed

---

## 🚨 Troubleshooting

### "Still shows 0 posts"
1. Clear browser cache (Ctrl+Shift+R)
2. Check `VITE_API_URL` is set correctly in Vercel
3. Verify backend returns data when accessed directly

### "Backend URL not working"
1. Check environment variables are set on Render
2. Check backend logs on Render for errors
3. Make sure `posts` table exists in Supabase

---

## 📝 Summary

**Localhost works** because it connects to `http://localhost:8000`

**Vercel needs** to connect to your deployed backend URL via `VITE_API_URL`

Once you add `VITE_API_URL` to Vercel and redeploy, it will work just like Tinder automation! 🚀
