# ✅ Make Dashboard Work on Vercel (Like Tinder Automation)

## The Problem:
Your deployed dashboard can't connect to Supabase because environment variables aren't set.

## The Solution (5 minutes):

---

## Step 1: Get Your Backend URL (if deployed)

### Option A: You have a backend deployed?
Find your backend URL (e.g., `https://work-notifier.onrender.com`)

### Option B: No backend deployed yet?
**You need the backend!** The dashboard needs an API to fetch data from Supabase.

**Quick Deploy Backend:**
1. Go to https://dashboard.render.com/register
2. Click "New +" → "Web Service"
3. Connect GitHub: `vladlevitin/work_notfier`
4. Settings:
   - Name: `work-notifier`
   - Root Directory: `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. **Environment Variables:**
   ```
   SUPABASE_URL=https://ipfghgunlexexcdlhrpr.supabase.co
   SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTM1NjAxNCwiZXhwIjoyMDg0OTMyMDE0fQ.9gT1bKQ7080rb3-Gu6aTrT17FvmOK4kmptDV4BSBp9c
   ```
6. Click "Create"
7. **Copy your backend URL** (e.g., `https://work-notifier.onrender.com`)

---

## Step 2: Configure Vercel to Use Backend

### Go to Vercel Dashboard:
https://vercel.com/dashboard

### Find Your Project:
Look for `work_notfier` or similar

### Add Environment Variable:
1. Click your project
2. Go to **"Settings"** tab
3. Click **"Environment Variables"**
4. Add this variable:

```
Name: VITE_API_URL
Value: https://work-notifier.onrender.com
```

(Replace with YOUR backend URL from Step 1)

5. Check **all three boxes**: Production, Preview, Development
6. Click **"Save"**

### Redeploy:
1. Go to **"Deployments"** tab
2. Find the latest deployment
3. Click the **"..."** menu (three dots)
4. Click **"Redeploy"**
5. Wait 1-2 minutes

---

## Step 3: Test Your Deployed Dashboard

### Open Your Vercel URL:
`https://your-project.vercel.app`

### Should Show:
- Total Posts: 16
- New Posts: 10
- All your Facebook posts

### Still Not Working?

**Test your backend:**
Open: `https://your-backend-url.onrender.com/api/stats`

Should show:
```json
{"total":16,"new":10,"by_group":[...]}
```

If not → Backend environment variables not set (go back to Step 1)

---

## Alternative: Direct Supabase Connection (No Backend)

If you don't want a separate backend, I can configure the frontend to connect DIRECTLY to Supabase (like some Tinder automation features).

**Would you prefer this?** It's simpler but less flexible.

Let me know!
