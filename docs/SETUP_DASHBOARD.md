# Dashboard Setup Guide

Follow these steps to get the dashboard running:

## Step 1: Create Database Table

1. Go to your Supabase SQL Editor:
   **https://supabase.com/dashboard/project/ipfghgunlexexcdlhrpr/sql/new**

2. Copy the entire contents of `supabase_schema.sql` and paste it into the editor

3. Click **"Run"** to execute the SQL

4. You should see: "Success. No rows returned"

## Step 2: Start the Backend API

Open a terminal in the project folder and run:

```powershell
cd backend
uvicorn app.main:app --reload --port 8000
```

You should see:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete.
```

Keep this terminal running!

## Step 3: Start the Frontend

Open a **NEW** terminal in the project folder and run:

```powershell
cd frontend
npm run dev
```

You should see:
```
VITE v5.x.x  ready in xxx ms

➜  Local:   http://localhost:5173/
```

## Step 4: Open Dashboard

Open your browser and go to: **http://localhost:5173/**

The dashboard should now work! 🎉

---

## Troubleshooting

### "Could not find the table 'public.posts'"
→ Run Step 1 again (create the database table)

### "Failed to fetch" error in dashboard
→ Make sure backend is running (Step 2)

### Backend won't start
→ Make sure you're in the `backend` folder and run:
```powershell
pip install fastapi uvicorn supabase python-dotenv
```

### Frontend won't start
→ Make sure you're in the `frontend` folder and run:
```powershell
npm install
```
