# Debug Connection Issue

## Step 1: Check What URL You're On

Look at your browser address bar. What do you see?

- `http://localhost:5174` → Local (should work)
- `https://something.vercel.app` → Deployed (needs configuration)
- Other → Tell me the URL

## Step 2: Open Browser Console

1. Press `F12` on your keyboard
2. Click the **"Console"** tab
3. Click the **🔄 Refresh** button on the dashboard
4. Look for RED error messages

### What Error Do You See?

#### Error 1: `Failed to fetch` or `net::ERR_NAME_NOT_RESOLVED`
**Meaning**: Frontend can't find the backend URL
**Fix**: Backend URL is wrong or not set

#### Error 2: `CORS policy` error
**Meaning**: Backend is blocking the frontend
**Fix**: Backend CORS not configured (but we did this)

#### Error 3: `404 Not Found`
**Meaning**: API endpoint doesn't exist
**Fix**: Backend isn't deployed correctly

#### Error 4: `500 Internal Server Error`
**Meaning**: Backend crashed
**Fix**: Environment variables not set on backend

## Step 3: Check Network Tab

1. In Browser DevTools (F12)
2. Click **"Network"** tab
3. Click 🔄 Refresh
4. Look for requests to `/api/stats` or `/api/posts`

### What Do You See?

- **Red (failed)**: Backend not reachable
- **Status 404**: Wrong URL
- **Status 500**: Backend error
- **Status 200**: Backend working! (cache issue)

## Step 4: Quick Tests

### Test A: Are you on localhost?
Open in a NEW tab: `http://localhost:5174`

Does it work? → Yes = Deployed version needs fixing, No = Local issue

### Test B: Is local backend running?
Open in a NEW tab: `http://localhost:8000/health`

Should show: `{"status":"healthy"}`

### Test C: Is local backend returning data?
Open in a NEW tab: `http://localhost:8000/api/stats`

Should show: `{"total":16,"new":10,...}`

---

## 📝 Tell Me:

1. **What URL are you on?** (localhost or deployed?)
2. **What error shows in Console?** (F12 → Console tab)
3. **Results of Test A, B, C above?**

Then I can fix the exact issue!
