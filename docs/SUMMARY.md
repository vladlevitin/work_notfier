# 🎉 Facebook Work Notifier Dashboard - Complete!

## ✅ What's Been Built

### 1. Database System 💾
- **SQLite database** to store all Facebook posts
- **Unique post IDs** to prevent duplicates
- **Automatic tracking** of which posts have been notified

### 2. Multi-Group Scraping 🔄
- Scrapes **2 Facebook groups** (easily add more)
- **Human-like behavior**: Random delays and scrolling
- **Robust extraction**: Post ID, timestamp, title, full text, URL

### 3. Smart Email Notifications 📧
- Only sends emails for **NEW relevant posts**
- Keyword filtering for driving/moving jobs
- Tracks notified posts in database
- **No duplicate notifications**

### 4. Modern Web Dashboard 🖥️
- **React + TypeScript** frontend
- **FastAPI** backend
- **Search & Filter** functionality
- **Infinite scroll** for performance
- **Beautiful card-based UI**

---

## 🚀 How to Use

### Run the Scraper
```bash
python main.py
```
**What it does:**
- Scrapes both Facebook groups
- Saves new posts to database
- Sends email for NEW relevant posts
- Marks notified posts

### View the Dashboard
```bash
# Quick start (opens both backend + frontend)
start_dashboard.bat
```
**Or manually:**
```bash
# Terminal 1: Backend
cd backend && uvicorn app.main:app --reload --port 8001

# Terminal 2: Frontend  
cd frontend && npm run dev
```

Then open: **http://localhost:5174**

---

## 📊 Dashboard Screenshots

### Main Dashboard
```
┌──────────────────────────────────────────────────────────┐
│  🚗 Facebook Work Notifier Dashboard                     │
├──────────────────────────────────────────────────────────┤
│  Stats: Total: 150 | New: 12 | Group 1: 85 | Group 2: 65│
├──────────────────────────────────────────────────────────┤
│  Search: [________] Group: [All ▼] ☐ Show only new  🔄  │
├──────────────────────────────────────────────────────────┤
│                                                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────┐ │
│  │ Post Card 1    │  │ Post Card 2    │  │ Post Card 3│ │
│  │ ✅ Notified    │  │                │  │ ✅ Notified│ │
│  │ 🆔 4434893...  │  │ 🆔 4434879...  │  │ 🆔 4434607│ │
│  │ 🕒 2 hours ago │  │ 🕒 3 hours ago │  │ 🕒 5 hrs  │ │
│  │ 📍 Group 1     │  │ 📍 Group 1     │  │ 📍 Group 2│ │
│  │ "Hei. Trenger │  │ "Er noen har..." │  │ "Bytte..." │ │
│  │  flytte..."    │  │                │  │            │ │
│  │ [View on FB →] │  │ [View on FB →] │  │ [View →]   │ │
│  └────────────────┘  └────────────────┘  └────────────┘ │
│                                                           │
│  Showing 20 of 150 posts (scroll for more)               │
└──────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

### Post Card Details
Each post shows:
- ✅ **Notified Badge** - Shows if email was sent
- 🆔 **Post ID** - Unique database identifier
- 🕒 **Posted Time** - From Facebook
- 📅 **Scraped Time** - When added to DB
- 📍 **Group Link** - Direct link to Facebook group
- **Full Text** - Complete post content
- **View Button** - Opens post on Facebook

### Search & Filter
- **Real-time search** - Find posts by keywords
- **Group filter** - Focus on specific groups
- **New posts only** - See unnotified posts
- **Infinite scroll** - Load more as you scroll

---

## 📁 File Structure

```
work_notifier/
├── 🐍 Python Scripts
│   ├── main.py              # Run this to scrape
│   ├── scraper.py           # Scraping logic
│   ├── database.py          # Database operations
│   ├── email_notifier.py    # Email sending
│   └── browser_manager.py   # Browser setup
│
├── 🌐 Backend API
│   └── backend/app/
│       ├── main.py          # FastAPI server
│       └── api/posts.py     # API endpoints
│
├── ⚛️ Frontend Dashboard
│   └── frontend/src/
│       ├── App.tsx          # Main app
│       ├── api/client.ts    # API client
│       └── pages/Posts.tsx  # Dashboard page
│
├── 💾 Database
│   └── facebook_posts.db    # SQLite database
│
└── 📚 Documentation
    ├── README.md            # Main docs
    ├── SETUP_GUIDE.md       # Detailed guide
    └── start_dashboard.bat  # Quick starter
```

---

## 🔑 Key Concepts

### Database Schema
```sql
CREATE TABLE posts (
    post_id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    text TEXT NOT NULL,
    url TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    group_name TEXT NOT NULL,
    group_url TEXT NOT NULL,
    scraped_at TEXT NOT NULL,
    notified BOOLEAN DEFAULT 0
);
```

### Workflow
```
1. Run main.py
   ↓
2. Scrape Facebook groups
   ↓
3. Save new posts to database
   ↓
4. Filter by keywords
   ↓
5. Check if already notified
   ↓
6. Send email for NEW matches
   ↓
7. Mark as notified in DB
   ↓
8. View all posts in dashboard
```

---

## 🎨 Technology Stack

### Backend
- **Python 3** - Main language
- **Selenium** - Web scraping
- **FastAPI** - API server
- **SQLite** - Database
- **Microsoft Graph API** - Email sending

### Frontend
- **React** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **CSS3** - Styling

---

## 🔧 Configuration

### Add Groups (main.py)
```python
FACEBOOK_GROUPS = [
    "https://www.facebook.com/groups/2014558715497143",
    "https://www.facebook.com/groups/857134597636986",
    # Add more here!
]
```

### Keywords (scraper.py)
```python
KEYWORDS = [
    "kjøre", "kjøring", "bil", 
    "flytte", "flytting", "transport",
    # Add your keywords!
]
```

### Scroll Steps (main.py)
```python
# More scrolls = more posts
scrape_facebook_group(driver, group_url, scroll_steps=5)
```

---

## 🎓 Next Steps

1. ✅ **Install dependencies**: `pip install -r requirements.txt`
2. ✅ **Run scraper**: `python main.py`
3. ✅ **Check email**: Look for notifications
4. ✅ **Start dashboard**: `start_dashboard.bat`
5. ✅ **Explore posts**: Search and filter in the UI

---

## 📞 Need Help?

- Check **README.md** for overview
- Read **SETUP_GUIDE.md** for detailed instructions
- Review code comments in Python files
- Check browser console for frontend errors
- Look at terminal output for backend logs

---

**Enjoy your new Facebook Work Notifier Dashboard!** 🚗💼✨
