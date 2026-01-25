# 🚗 Facebook Work Notifier Dashboard

A complete system for scraping, storing, and monitoring Facebook job posts with email notifications and a web dashboard.

## Features

- **Multi-Group Scraping**: Monitors multiple Facebook groups simultaneously
- **Smart Duplicate Detection**: Uses post IDs to prevent duplicate entries
- **Database Storage**: SQLite database for persistent post storage
- **Web Dashboard**: Modern React dashboard with search and filtering
- **Email Notifications**: Sends emails only for NEW relevant posts matching keywords
- **Human-like Behavior**: Random delays and scrolling patterns to avoid detection

## Setup

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file with your Microsoft Graph API credentials:

```env
TENANT_ID=your_tenant_id
CLIENT_ID=your_client_id
CLIENT_SECRET=your_client_secret
SENDER_EMAIL=your_email@example.com
```

### 3. Install Frontend Dependencies

```bash
cd frontend
npm install
```

## Usage

### Scrape Facebook Groups

Run the scraper to collect posts from configured Facebook groups:

```bash
python main.py
```

The scraper will:
1. Initialize the database (if not already created)
2. Open Microsoft Edge with your dedicated profile
3. Navigate to each Facebook group
4. Scroll 5 times and collect all posts
5. Save new posts to the database
6. Send email notifications for NEW posts matching keywords
7. Mark notified posts in the database

### Start the Dashboard

#### Backend API:

```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

#### Frontend:

```bash
cd frontend
npm run dev
```

Then open http://localhost:5174 in your browser.

## Dashboard Features

### Search & Filter

- **Search Bar**: Search posts by title or content
- **Group Filter**: Filter by specific Facebook group
- **Show Only New**: Display only posts that haven't been notified yet

### Post Cards

Each post card displays:
- 🆔 **Post ID**: Unique identifier for database tracking
- 🕒 **Posted**: Original timestamp from Facebook
- 📅 **Scraped**: When the post was added to the database
- 📍 **Group**: Link to the Facebook group
- ✅ **Notified Badge**: Shows if email was sent for this post

## Configuration

### Facebook Groups

Edit `main.py` to add/remove Facebook groups:

```python
FACEBOOK_GROUPS = [
    "https://www.facebook.com/groups/2014558715497143",
    "https://www.facebook.com/groups/857134597636986",
]
```

### Keywords

Edit `scraper.py` to modify the keywords for filtering relevant posts:

```python
KEYWORDS = [
    "kjøre", "kjøring", "bil", "flytte", "flytting", 
    "transport", "sjåfør", "fører", "førerkort", 
    "levering", "hente", "frakt", "flyttejobb"
]
```

### Scroll Steps

Adjust the number of scrolls per group in `main.py`:

```python
posts = scrape_facebook_group(driver, group_url, scroll_steps=5)
```

## Architecture

### Backend (Python + FastAPI)

- `main.py`: Entry point for scraping
- `scraper.py`: Facebook scraping logic with Selenium
- `database.py`: SQLite database operations
- `email_notifier.py`: Email notifications via Microsoft Graph API
- `browser_manager.py`: Edge browser profile management
- `backend/app/`: FastAPI web server for dashboard API

### Frontend (React + TypeScript)

- Modern card-based UI with infinite scroll
- Real-time search with debouncing
- Responsive grid layout
- Direct links to Facebook posts and groups

### Database Schema

**Posts Table:**
- `post_id` (TEXT, PRIMARY KEY): Unique post identifier
- `title` (TEXT): Post title (first line or 60 chars)
- `text` (TEXT): Full post content
- `url` (TEXT): Direct link to the post
- `timestamp` (TEXT): When the post was made on Facebook
- `group_name` (TEXT): Name of the Facebook group
- `group_url` (TEXT): URL of the Facebook group
- `scraped_at` (TEXT): When the post was scraped
- `notified` (BOOLEAN): Whether email notification was sent

## Workflow

1. **Scrape**: Run `python main.py` to scrape groups and save to database
2. **Auto-notify**: Script automatically sends email for NEW relevant posts
3. **Review**: Open dashboard to view all posts with search/filter
4. **Repeat**: Run scraper periodically to check for new posts

## Tips

- The Edge profile in `edge_profile/` stores your Facebook login, so you only need to log in once
- Posts with `post_id="unknown"` are still saved but may be harder to deduplicate
- The dashboard updates in real-time as you scrape new posts
- Use the search bar to find specific keywords beyond the automated filter
