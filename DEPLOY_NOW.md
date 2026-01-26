# 🚀 Deploy Your Dashboard RIGHT NOW

## ✅ I've configured everything. Just follow these steps:

---

## Step 1: Deploy Backend to Render (5 minutes)

### 1.1 Go to Render
**https://dashboard.render.com/register**

Sign up with GitHub if you haven't already.

### 1.2 Create New Web Service
1. Click **"New +"** button (top right)
2. Select **"Web Service"**
3. Connect your GitHub repository: `vladlevitin/work_notfier`

### 1.3 Configure Service
Use these EXACT settings:

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

### 1.4 Add Environment Variables
Click **"Advanced"** → **"Add Environment Variable"**

Add these THREE variables (copy-paste exactly):

**Variable 1:**
```
Name: SUPABASE_URL
Value: https://ipfghgunlexexcdlhrpr.supabase.co
```

**Variable 2:**
```
Name: SUPABASE_KEY
Value: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNTYwMTQsImV4cCI6MjA4NDkzMjAxNH0.YlIEHih0-K_JC-Bak3JHTicLYA2exRS_V2hKfOzH0qM
```

**Variable 3:**
```
Name: SUPABASE_SERVICE_KEY
Value: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTM1NjAxNCwiZXhwIjoyMDg0OTMyMDE0fQ.9gT1bKQ7080rb3-Gu6aTrT17FvmOK4kmptDV4BSBp9c
```

### 1.5 Deploy
1. Click **"Create Web Service"**
2. Wait 2-3 minutes for deployment
3. **COPY YOUR BACKEND URL** (looks like: `https://work-notifier-backend.onrender.com`)

### 1.6 Test Backend
Open in browser:
```
https://your-backend-url.onrender.com/health
```

Should show: `{"status":"healthy"}`

---

## Step 2: Deploy Frontend to Vercel (3 minutes)

### 2.1 Go to Vercel
**https://vercel.com/signup**

Sign up with GitHub if you haven't already.

### 2.2 Import Project
1. Click **"Add New..."** → **"Project"**
2. Find your repository: `vladlevitin/work_notfier`
3. Click **"Import"**

### 2.3 Configure Project
Use these EXACT settings:

```
Framework Preset: Vite
Root Directory: frontend
Build Command: npm run build
Output Directory: dist
Install Command: npm install
```

### 2.4 Add Environment Variable
Click **"Environment Variables"** section

**Add this ONE variable:**
```
Name: VITE_API_URL
Value: [YOUR BACKEND URL FROM STEP 1.5]
```

Example: `https://work-notifier-backend.onrender.com`

Check all three boxes: Production, Preview, Development

### 2.5 Deploy
1. Click **"Deploy"**
2. Wait 1-2 minutes
3. **COPY YOUR FRONTEND URL** (looks like: `https://work-notfier.vercel.app`)

---

## Step 3: Test Everything

### 3.1 Test Backend
Open: `https://your-backend-url.onrender.com/api/stats`

Should show:
```json
{"total":16,"new":10,"by_group":[...]}
```

### 3.2 Test Frontend
Open: `https://your-frontend-url.vercel.app`

Should show:
- Total Posts: 16
- New Posts: 10
- All your Facebook posts displayed

---

## 🎉 DONE!

Your dashboard is now live and accessible from anywhere!

---

## 🔧 If Something Goes Wrong

### Backend Returns 500 Error
→ Environment variables not set. Go back to Step 1.4

### Frontend Shows "Failed to fetch"
→ `VITE_API_URL` not set. Go to Vercel → Settings → Environment Variables → Add it → Redeploy

### Backend URL Not Working
→ Check Render logs for errors. Go to your service → Logs tab

---

## 📞 Need Help?

Share:
1. Your backend URL
2. Your frontend URL
3. Any error messages from the logs

And I'll help you debug!
