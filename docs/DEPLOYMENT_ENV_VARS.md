# Environment Variables for Deployment

## Backend Environment Variables (Render/Railway)

Add these environment variables to your deployment platform:

### Required Variables:

```
SUPABASE_URL=https://ipfghgunlexexcdlhrpr.supabase.co

SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjkzNTYwMTQsImV4cCI6MjA4NDkzMjAxNH0.YlIEHih0-K_JC-Bak3JHTicLYA2exRS_V2hKfOzH0qM

SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlwZmdoZ3VubGV4ZXhjZGxocnByIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc2OTM1NjAxNCwiZXhwIjoyMDg0OTMyMDE0fQ.9gT1bKQ7080rb3-Gu6aTrT17FvmOK4kmptDV4BSBp9c
```

### Optional (New Supabase Keys):

```
SUPABASE_PUBLISHABLE_KEY=sb_publishable_NBKm20aUNSsYXM4D1_e_yw_ONP-Swit

SUPABASE_SECRET_KEY=sb_secret_Dfk_uKETUN9ZjVbGs73Swg_ZJ8rNFge
```

---

## Frontend Environment Variables (Vercel)

Add this to Vercel environment variables:

```
VITE_API_URL=https://your-backend-url.onrender.com
```

**Note**: Replace `your-backend-url.onrender.com` with your actual backend URL from Render/Railway

---

## How Backend Uses These Variables

### `supabase_db.py` uses:
- `SUPABASE_URL` - Project URL
- Priority order for auth:
  1. `SUPABASE_SERVICE_KEY` (highest priority - full permissions)
  2. `SUPABASE_SECRET_KEY` (alternative service key)
  3. `SUPABASE_KEY` (fallback anon key)

The code automatically uses the most privileged key available.

---

## Verification

After deployment, test your backend:

```bash
curl https://your-backend-url.onrender.com/health
curl https://your-backend-url.onrender.com/api/stats
```

Should return:
```json
{"status": "healthy"}
{"total": 16, "new": 10, "by_group": [...]}
```
