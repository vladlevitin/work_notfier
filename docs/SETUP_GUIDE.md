# 🚗 Facebook Work Notifier - Complete Setup Guide

## What's Been Created

Your Facebook Work Notifier now has:

1. **Database System** - SQLite database to store all posts with unique post IDs
2. **Multi-Group Support** - Scrapes 2 Facebook groups (easily expandable)
3. **Smart Notifications** - Only sends emails for NEW posts that haven't been notified yet
4. **Web Dashboard** - Modern React dashboard to view, search, and filter all posts
5. **API Backend** - FastAPI server to serve the dashboard

## File Structure

```
work_notifier/
├── main.py                    # Main scraper script (run this)
├── scraper.py                 # Facebook scraping logic
├── database.py                # Database operations
├── email_notifier.py          # Email notifications
├── browser_manager.py         # Edge browser management
├── requirements.txt           # Python dependencies
├── facebook_posts.db          # SQLite database (created automatically)
├── .env                       # Your API credentials
├── backend/
│   └── app/
│       ├── main.py           # FastAPI application
│       └── api/
│           └── posts.py      # API endpoints
└── frontend/
    ├── package.json          # Node dependencies
    ├── src/
    │   ├── main.tsx          # React entry point
    │   ├── App.tsx           # Main app component
    │   ├── api/
    │   │   └── client.ts     # API client
    │   └── pages/
    │       ├── Posts.tsx     # Dashboard page
    │       └── Posts.css     # Dashboard styles
    └── vite.config.ts        # Vite configuration
```

## Quick Start

### 1. Install Dependencies

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies (if you want to use the dashboard)
cd frontend
npm install
```

### 2. Run the Scraper

```bash
python main.py
```

This will:
- Initialize the database on first run
- Open Edge and navigate to both Facebook groups
- Scrape posts from each group (5 scrolls per group)
- Save new posts to the database
- Filter for driving/moving keywords
- Send email notification for NEW relevant posts ONLY
- Mark notified posts in the database

### 3. View the Dashboard (Optional)

#### Option A: Use the startup script

Windows Batch:
```bash
start_dashboard.bat
```

PowerShell:
```powershell
.\start_dashboard.ps1
```

#### Option B: Start manually

Terminal 1 (Backend):
```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

Terminal 2 (Frontend):
```bash
cd frontend
npm run dev
```

Then open: http://localhost:5174

## How It Works

### Scraping Flow

1. **Loop through groups**: Iterates through both Facebook groups
2. **Scroll and collect**: Scrolls 5 times per group with human-like delays
3. **Extract details**: Captures post ID, title, text, URL, timestamp, group info
4. **Check database**: Only saves NEW posts (duplicates are skipped)
5. **Filter keywords**: Checks for driving/moving job keywords
6. **Smart notification**: Only sends email for NEW relevant posts
7. **Mark notified**: Updates database so the same post isn't notified again

### Dashboard Features

#### Stats Bar
- Total posts in database
- Number of new posts (not notified yet)
- Posts per group

#### Search & Filters
- **Search**: Search by title or content (debounced for performance)
- **Group Filter**: Filter by specific Facebook group
- **Show Only New**: Display only posts that haven't been notified
- **Refresh**: Reload stats and posts

#### Post Cards
Each post shows:
- 🆔 Post ID (for database tracking)
- 🕒 Posted time (from Facebook)
- 📅 Scraped time (when added to database)
- 📍 Group link
- ✅ Notified badge (if email was sent)
- Full post text
- Direct link to view on Facebook

### Database Structure

**posts table:**
- `post_id` (TEXT, PRIMARY KEY) - Unique post identifier from Facebook
- `title` (TEXT) - First line or 60 chars of post
- `text` (TEXT) - Full post content
- `url` (TEXT) - Direct link to the post
- `timestamp` (TEXT) - When posted on Facebook
- `group_name` (TEXT) - Name of the Facebook group
- `group_url` (TEXT) - URL of the Facebook group
- `scraped_at` (TEXT) - When added to database
- `notified` (BOOLEAN) - Whether email was sent (0 or 1)

## Configuration

### Add More Facebook Groups

Edit `main.py`:

```python
FACEBOOK_GROUPS = [
    "https://www.facebook.com/groups/2014558715497143",
    "https://www.facebook.com/groups/857134597636986",
    "https://www.facebook.com/groups/YOUR_NEW_GROUP_ID",  # Add here
]
```

### Change Keywords

Edit `scraper.py`:

```python
KEYWORDS = [
    "kjøre", "kjøring", "bil", "flytte", "flytting", 
    "transport", "sjåfør", "fører", "førerkort", 
    "levering", "hente", "frakt", "flyttejobb",
    # Add your keywords here
]
```

### Adjust Scroll Steps

In `main.py`, change the `scroll_steps` parameter:

```python
posts = scrape_facebook_group(driver, group_url, scroll_steps=10)  # More scrolls = more posts
```

## API Endpoints

### GET /api/posts
Get posts with filtering

Query params:
- `limit` (int, 1-1000): Max posts to return
- `offset` (int): Skip N posts for pagination
- `group_url` (string, optional): Filter by group
- `search` (string, optional): Search in title/text
- `only_new` (boolean): Only unnotified posts

Example:
```
GET /api/posts?limit=20&search=flytting&only_new=true
```

### GET /api/stats
Get database statistics

Returns:
```json
{
  "total": 150,
  "new": 12,
  "by_group": [
    {"group": "Småjobber utføres og ønskes i Oslo og Viken", "count": 85},
    {"group": "Group 2", "count": 65}
  ]
}
```

## Workflow

### Daily Use

1. **Morning**: Run `python main.py` to scrape new posts
   - Get email notification for NEW driving/moving jobs
   
2. **During the day**: Check dashboard to review all posts
   - Use search to find specific keywords
   - Filter by group to focus on one group
   
3. **Evening**: Run `python main.py` again to catch afternoon posts

### First Run

On the first run:
- Database is automatically created
- You may need to log into Facebook in the Edge browser
- The profile is saved in `edge_profile/` so you won't need to log in again

## Troubleshooting

### "DevToolsActivePort file doesn't exist"
- The script automatically handles this by cleaning up lock files
- If it persists, delete the `edge_profile/` folder and restart

### No posts found
- Make sure you're logged into Facebook
- Check that the group URLs are correct
- Increase `scroll_steps` to load more posts

### Email not sending
- Check your `.env` file has correct credentials
- Verify Microsoft Graph API permissions
- Check `main.py` output for error messages

### Dashboard not loading
- Make sure both backend (port 8001) and frontend (port 5174) are running
- Check browser console for errors
- Try `npm install` again in the frontend folder

## Tips

1. **Run regularly**: Schedule `main.py` to run every few hours to catch new posts
2. **Backup database**: The `facebook_posts.db` file contains all your data
3. **Customize keywords**: Add industry-specific terms to your keyword list
4. **Check logs**: The scraper prints detailed logs to help debug issues
5. **Use dashboard search**: Find posts even if they weren't in the initial keyword filter

## Next Steps

### Possible Enhancements

1. **Scheduling**: Use Windows Task Scheduler or cron to run the scraper automatically
2. **More groups**: Add more Facebook groups to monitor
3. **Advanced filters**: Add filters for date ranges, post length, etc.
4. **Export**: Add CSV/Excel export functionality
5. **Notifications**: Add browser push notifications in the dashboard
6. **Mobile**: Make the dashboard mobile-responsive

---

## Questions?

Check the README.md for more detailed documentation, or review the code comments in each Python file.

Happy job hunting! 🚗💼
