# 📁 Project Structure

## Overview

```
work_notifier/
├── 📁 config/                   # Configuration files
│   ├── groups.json             # ⭐ Facebook groups to scrape
│   └── settings.py             # Application settings
│
├── 📁 src/                      # Source code
│   ├── scraper/                # Facebook scraping logic
│   │   ├── scraper.py          # Main scraping functions
│   │   ├── browser_manager.py  # Browser automation setup
│   │   └── timestamp_parser.py # Parse Facebook timestamps
│   │
│   ├── ai/                     # AI processing
│   │   └── ai_processor.py     # OpenAI integration
│   │
│   ├── database/               # Database operations
│   │   └── supabase_db.py      # Supabase client
│   │
│   └── notifications/          # Email notifications
│       └── email_notifier.py   # Gmail integration
│
├── 📁 scripts/                  # Utility scripts
│   ├── test_all_connections.py
│   ├── setup_database.py
│   └── ...
│
├── 📁 migrations/               # Database migrations
│   ├── add_ai_columns.sql
│   └── add_posted_at_column.sql
│
├── 📁 docs/                     # Documentation
│   ├── README.md
│   ├── DATABASE_MIGRATION.md
│   ├── AI_SETUP.md
│   └── PROJECT_STRUCTURE.md    # This file
│
├── 📁 frontend/                 # React dashboard
│   └── src/
│       ├── pages/Posts.tsx     # Main dashboard
│       └── api/client.ts       # API client
│
├── 📁 api/                      # Vercel serverless functions
│   ├── posts.ts                # Get posts API
│   └── stats.ts                # Get stats API
│
├── 📁 backend/                  # Old FastAPI backend (archived)
│
├── main.py                      # ⭐ Main entry point
├── requirements-local.txt       # Python dependencies
├── .env                        # Environment variables (not in git)
└── vercel.json                 # Vercel deployment config
```

---

## Key Files

### ⭐ Must Know Files

#### `config/groups.json` - Facebook Groups Configuration
**This is where you add/remove Facebook groups!**

```json
{
  "facebook_groups": [
    {
      "name": "Group Name Here",
      "url": "https://www.facebook.com/groups/123456",
      "enabled": true,
      "scroll_steps": 5,
      "description": "Optional description"
    }
  ]
}
```

**To add a new group:**
1. Open `config/groups.json`
2. Copy an existing group object
3. Update the `name`, `url`, and `description`
4. Set `enabled: true`
5. Save and run `python main.py`

#### `main.py` - Main Script
Run this to scrape Facebook groups:
```bash
python main.py
```

#### `.env` - Environment Variables
Store your API keys here:
```
SUPABASE_URL=your_url
SUPABASE_KEY=your_key
OPENAI_API_KEY=your_openai_key
GMAIL_APP_PASSWORD=your_gmail_password
```

---

## Module Structure

### `src/scraper/` - Scraping Module
- **scraper.py** - Core scraping logic, extracts posts from Facebook
- **browser_manager.py** - Manages Edge browser instance
- **timestamp_parser.py** - Parses Facebook timestamps ("7h", "24 January at 08:42")

### `src/ai/` - AI Module
- **ai_processor.py** - Uses OpenAI to extract:
  - Category (Transport, Painting, Cleaning, etc.)
  - Location (Oslo, Asker, etc.)
  - Features (urgency, price, contact method)

### `src/database/` - Database Module
- **supabase_db.py** - All Supabase operations:
  - Save posts
  - Check for duplicates
  - Mark as notified
  - Get statistics

### `src/notifications/` - Notifications Module
- **email_notifier.py** - Send email alerts via Gmail

---

## Configuration System

### Groups Configuration (`config/groups.json`)

**Structure:**
```json
{
  "facebook_groups": [
    {
      "name": "Human-readable name",
      "url": "Facebook group URL",
      "enabled": true,
      "scroll_steps": 5,
      "description": "Optional notes"
    }
  ],
  "notes": {
    "how_to_add_group": "Instructions...",
    "required_fields": ["name", "url", "enabled"],
    "optional_fields": ["scroll_steps", "description"]
  }
}
```

**Fields:**
- `name`: Display name for the group
- `url`: Full Facebook group URL
- `enabled`: `true` to scrape, `false` to skip
- `scroll_steps`: How many times to scroll (default: 5)
- `description`: Optional notes about the group

### Application Settings (`config/settings.py`)

Manages:
- Loading groups from JSON
- Search keywords
- AI configuration
- Category definitions

---

## Frontend Structure

### Dashboard (`frontend/src/pages/Posts.tsx`)
- Display posts in grid layout
- Filter by group, category, location
- Show only new posts toggle
- Search functionality
- Category and location badges

### API Client (`frontend/src/api/client.ts`)
- Fetch posts from Vercel API
- Fetch statistics
- TypeScript interfaces for type safety

---

## Backend API (`api/`)

Vercel serverless functions in TypeScript:

### `api/posts.ts`
- GET `/api/posts` - Fetch posts with filters
- Query params: `limit`, `offset`, `group_url`, `search`, `category`, `location`, `only_new`

### `api/stats.ts`
- GET `/api/stats` - Get database statistics
- Returns: total posts, new posts, posts by group

---

## Deployment

### Frontend + API (Vercel)
- **URL**: https://work-notfier.vercel.app
- **Auto-deploys** on push to `main` branch
- Environment variables set in Vercel dashboard

### Database (Supabase)
- **Dashboard**: https://supabase.com/dashboard
- **Tables**: `posts`
- **Run migrations** in SQL Editor

---

## Workflow

### Adding a New Facebook Group

1. Open `config/groups.json`
2. Add new group object:
```json
{
  "name": "New Group Name",
  "url": "https://www.facebook.com/groups/YOUR_GROUP_ID",
  "enabled": true,
  "scroll_steps": 5,
  "description": "What this group is for"
}
```
3. Save file
4. Run: `python main.py`
5. Posts from new group will be scraped!

### Running the Scraper

```bash
# Activate environment (if using venv)
# python -m venv venv
# venv\Scripts\activate

# Install dependencies
pip install -r requirements-local.txt

# Run scraper
python main.py
```

### Deploying Changes

```bash
# Commit changes
git add .
git commit -m "Your changes"
git push

# Vercel auto-deploys!
# Check: https://work-notfier.vercel.app
```

---

## Maintenance

### Clean Up Old Posts
```sql
-- In Supabase SQL Editor
DELETE FROM posts WHERE scraped_at < NOW() - INTERVAL '30 days';
```

### Re-process Posts with AI
```sql
-- Mark all as unprocessed
UPDATE posts SET ai_processed = FALSE;

-- Then run scraper to re-process
```

### Check Statistics
```bash
python scripts/test_all_connections.py
```

---

## Troubleshooting

### Groups not loading?
- Check `config/groups.json` is valid JSON
- Ensure `enabled: true` for groups you want to scrape

### Scraper not finding posts?
- Check Facebook login is active (uses Edge profile)
- Increase `scroll_steps` in groups.json

### AI not working?
- Check `OPENAI_API_KEY` in `.env`
- Run database migration: `migrations/add_ai_columns.sql`

### Dashboard not showing data?
- Check Vercel deployment logs
- Verify Supabase environment variables
- Run: `scripts/test_all_connections.py`

---

## Development

### Running Locally

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# Opens http://localhost:5173
```

**API Functions:**
```bash
# Install Vercel CLI
npm i -g vercel

# Run locally
vercel dev
# API available at http://localhost:3000/api
```

### Testing

```bash
# Test Supabase connection
python scripts/test_supabase_connection.py

# Test all connections
python scripts/test_all_connections.py

# Test groups loading
python config/settings.py
```

---

## Version History

- **v2.0.0** - Restructured project, added groups.json configuration
- **v1.5.0** - Added AI categorization and location extraction
- **v1.0.0** - Initial release with basic scraping and email notifications
