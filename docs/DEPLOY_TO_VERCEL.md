# 🚀 Deploy to Vercel (Like Tinder Automation)

## ✅ Setup Complete!

Your project is now configured to deploy everything on Vercel with automatic GitHub integration.

---

## Step 1: Push to GitHub

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Configure for Vercel deployment"

# Add your GitHub repository as remote
git remote add origin https://github.com/YOUR_USERNAME/work_notifier.git

# Push to GitHub
git push -u origin main
```

---

## Step 2: Deploy on Vercel

### A. Go to Vercel Dashboard
👉 https://vercel.com/dashboard

### B. Import GitHub Repository
1. Click **"Add New..."** → **"Project"**
2. Find **"work_notifier"** in your GitHub repos
3. Click **"Import"**

### C. Configure Project
1. **Framework Preset**: Vite
2. **Root Directory**: Leave blank (uses root)
3. **Build Command**: Auto-detected from `vercel.json`
4. **Output Directory**: Auto-detected from `vercel.json`

### D. Add Environment Variables (IMPORTANT!)
Click **"Environment Variables"** and add these:

```
SUPABASE_URL = https://ipfghgunlexexcdlhrpr.supabase.co

SUPABASE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNTYwMTQsImV4cCI6MjA4NDkzMjAxNH0.YlIEHih0-K_JC-Bak3JHTicLYA2exRS_V2hKfOzH0qM

SUPABASE_SERVICE_KEY = eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTM1NjAxNCwiZXhwIjoyMDg0OTMyMDE0fQ.9gT1bKQ7080rb3-Gu6aTrT17FvmOK4kmptDV4BSBp9c
```

**Check all three boxes**: Production, Preview, Development

### E. Deploy
Click **"Deploy"** and wait 2-3 minutes!

---

## Step 3: Test Your Deployment

### Your Vercel URL:
`https://work-notifier-YOUR_USERNAME.vercel.app`

### Test API:
`https://work-notifier-YOUR_USERNAME.vercel.app/api/stats`

Should return:
```json
{
  "total": 16,
  "new": 10,
  "by_group": [...]
}
```

### Test Dashboard:
`https://work-notifier-YOUR_USERNAME.vercel.app`

Should show your posts!

---

## 🔄 Automatic Updates

**From now on:**
1. Make changes to your code
2. Push to GitHub: `git push`
3. Vercel automatically redeploys! ✨

---

## 📊 What's Deployed:

✅ **Frontend**: React dashboard (from `frontend/`)  
✅ **Backend API**: Serverless functions (from `api/`)  
✅ **Database**: Supabase (automatically connected)

Everything in one Vercel project - just like your Tinder automation!

---

## 🐛 Troubleshooting

### API returns 404?
- Check environment variables are set in Vercel dashboard
- Redeploy: Go to "Deployments" → Click "..." → "Redeploy"

### Dashboard shows no data?
- Test the API endpoint directly: `/api/stats`
- Check browser console for errors (F12)

### Still not working?
Run the test locally first:
```bash
python test_all_connections.py
```

Make sure local works before deploying!
