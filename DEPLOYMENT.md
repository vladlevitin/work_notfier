# Deployment Guide

## Prerequisites
- GitHub account (already have)
- Vercel account (free)
- Render account (free)

---

## Part 1: Deploy Backend to Render

### Step 1: Create Render Account
1. Go to: https://render.com
2. Sign up with your GitHub account
3. Authorize Render to access your repositories

### Step 2: Create New Web Service
1. Click **"New"** → **"Web Service"**
2. Connect your GitHub repository: `vladlevitin/work_notfier`
3. Configure:
   - **Name**: `work-notifier-backend`
   - **Region**: Choose closest to you
   - **Branch**: `main`
   - **Root Directory**: `backend`
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

### Step 3: Add Environment Variables
In Render dashboard, go to **Environment** tab and add:

```
SUPABASE_URL=https://ipfghgunlexexcdlhrpr.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNTYwMTQsImV4cCI6MjA4NDkzMjAxNH0.YlIEHih0-K_JC-Bak3JHTicLYA2exRS_V2hKfOzH0qM
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTM1NjAxNCwiZXhwIjoyMDg0OTMyMDE0fQ.9gT1bKQ7080rb3-Gu6aTrT17FvmOK4kmptDV4BSBp9c
```

### Step 4: Deploy
1. Click **"Create Web Service"**
2. Wait for deployment (2-3 minutes)
3. Your backend will be live at: `https://work-notifier-backend.onrender.com`

---

## Part 2: Deploy Frontend to Vercel

### Step 1: Update Frontend API URL
1. Create `frontend/.env.production`:
```
VITE_API_URL=https://work-notifier-backend.onrender.com
```

### Step 2: Update API Client
Edit `frontend/src/api/client.ts` to use environment variable:
```typescript
const API_BASE = import.meta.env.VITE_API_URL || '/api';
```

### Step 3: Deploy to Vercel
1. Go to: https://vercel.com
2. Sign up with your GitHub account
3. Click **"Add New"** → **"Project"**
4. Import `vladlevitin/work_notfier`
5. Configure:
   - **Framework Preset**: Vite
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
6. Add Environment Variable:
   - **Name**: `VITE_API_URL`
   - **Value**: `https://work-notifier-backend.onrender.com`
7. Click **"Deploy"**

### Step 4: Access Your Dashboard
Your dashboard will be live at: `https://your-project.vercel.app`

---

## Alternative: Simple Vercel Deployment

### Quick Deploy (Recommended)
1. Push your code to GitHub
2. Go to https://vercel.com/new
3. Import your repository
4. Vercel will auto-detect Vite and deploy
5. Add environment variable for backend URL

---

## Notes

### Backend (Render Free Tier)
- Spins down after 15 minutes of inactivity
- First request after spin-down takes ~30 seconds
- Upgrade to paid tier ($7/month) for always-on

### Frontend (Vercel)
- Always fast and available
- Automatic HTTPS
- Global CDN

### Update vercel.json
After deploying backend, update `vercel.json` with your actual backend URL:
```json
{
  "rewrites": [
    {
      "source": "/api/:path*",
      "destination": "https://work-notifier-backend.onrender.com/api/:path*"
    }
  ]
}
```

---

## Testing Deployment

### Test Backend
```bash
curl https://work-notifier-backend.onrender.com/api/stats
```

### Test Frontend
Open: https://your-project.vercel.app

---

## Continuous Deployment

Both services auto-deploy when you push to GitHub:
- Push to `main` branch
- Backend redeploys on Render automatically
- Frontend redeploys on Vercel automatically
