# 🚗 Facebook Work Notifier

> **AI-powered job board that scrapes Facebook groups, categorizes posts, and sends email notifications**

[![Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-black?logo=vercel)](https://work-notfier.vercel.app)
[![TypeScript](https://img.shields.io/badge/TypeScript-007ACC?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![React](https://img.shields.io/badge/React-20232A?logo=react&logoColor=61DAFB)](https://reactjs.org/)
[![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white)](https://www.python.org/)

---

## 🎯 Features

- ✅ **Automated Scraping** - Scrapes multiple Facebook groups automatically
- 🤖 **AI Categorization** - Uses OpenAI to extract category, location, and features
- 📊 **Modern Dashboard** - React dashboard with filtering and search
- 📧 **Email Notifications** - Gmail alerts for new matching posts
- 🔍 **Smart Processing** - Only processes new posts (saves API costs)
- 📱 **Mobile Responsive** - Works on desktop, tablet, and mobile

---

## 🚀 Quick Start

### 1. Add Facebook Groups

Edit `config/groups.json` to add your Facebook groups:

```json
{
  "facebook_groups": [
    {
      "name": "Your Group Name",
      "url": "https://www.facebook.com/groups/123456",
      "enabled": true,
      "scroll_steps": 5
    }
  ]
}
```

### 2. Run Scraper

```bash
python main.py
```

### 3. View Dashboard

Open: **https://work-notfier.vercel.app**

---

## 📁 Project Structure

```
work_notifier/
├── config/              # ⭐ Configuration (groups.json)
├── src/                 # Source code
│   ├── scraper/         # Facebook scraping
│   ├── ai/              # AI processing
│   ├── database/        # Supabase operations
│   └── notifications/   # Email alerts
├── scripts/             # Utility scripts
├── migrations/          # Database migrations
├── docs/                # Documentation
├── frontend/            # React dashboard
├── api/                 # Vercel serverless functions
└── main.py              # ⭐ Main entry point
```

[📖 Detailed Project Structure](docs/PROJECT_STRUCTURE.md)

---

## 📚 Documentation

- 🏗️ **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Folder organization and key files
- 🗄️ **[Database Migration](docs/DATABASE_MIGRATION.md)** - How to run SQL migrations
- 🤖 **[AI Setup](docs/AI_SETUP.md)** - Configure AI categorization
- 🚀 **[Deployment Guide](docs/VERCEL_SETUP.md)** - Deploy to Vercel

---

## 🔧 Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- Facebook account (for scraping)
- Supabase account (database)
- OpenAI API key (for AI features)
- Gmail account (for notifications)

### Installation

```bash
# Install Python dependencies
pip install -r requirements-local.txt

# Install frontend dependencies
cd frontend
npm install

# Install API dependencies
cd ../api
npm install
```

### Environment Variables

Create `.env` file in root:

```bash
# Supabase
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_SERVICE_KEY=your_service_key

# OpenAI (for AI categorization)
OPENAI_API_KEY=your_openai_key

# Gmail (for notifications)
GMAIL_APP_PASSWORD=your_gmail_app_password
GMAIL_USER=your_email@gmail.com
EMAIL_TO=recipient@email.com
```

---

## 🎨 Dashboard Features

### Filters
- 📂 **Category** - Transport, Painting, Cleaning, Plumbing, Assembly, General
- 📍 **Location** - Oslo, Asker, Viken, etc.
- 🔍 **Search** - Search in title and text
- ✨ **Show Only New** - Filter unnotified posts

### Post Cards
- 🕒 **Posted Date** - When job was posted (top of card)
- 🏷️ **Category Badge** - AI-extracted category with icon
- 📍 **Location Tag** - AI-extracted location
- 🔗 **Facebook Link** - Direct link to original post

---

## 🤖 AI Features

### Smart Categorization
- **Transport / Moving** 🚚 - Moving jobs, transport, delivery
- **Painting / Renovation** 🎨 - Painting, renovation, carpentry
- **Cleaning / Garden** 🧹 - Cleaning, garden work, snow removal
- **Plumbing / Electrical** 🔧 - Plumbing, electrical work
- **Assembly / Furniture** 🪑 - IKEA assembly, furniture installation
- **General** 📦 - Everything else

### Location Extraction
Identifies Norwegian cities and areas:
- Oslo, Asker, Viken, Bergen, Trondheim, etc.
- Specific neighborhoods (Mortensrud, Snarøya, etc.)

### Cost Optimization
- ✅ Only processes **new** posts
- ✅ Checks post ID before using AI
- ✅ Updates old posts that weren't AI-processed
- 💰 Saves API calls and money!

---

## 🛠️ Usage

### Scrape Facebook Groups

```bash
python main.py
```

### Test Connections

```bash
python scripts/test_all_connections.py
```

### Run Frontend Locally

```bash
cd frontend
npm run dev
# Opens http://localhost:5173
```

### Deploy to Vercel

```bash
git add .
git commit -m "Your changes"
git push
# Auto-deploys to Vercel!
```

---

## 📊 Tech Stack

### Frontend
- **React** - UI framework
- **TypeScript** - Type safety
- **Vite** - Build tool
- **CSS3** - Styling

### Backend
- **Python** - Scraping and AI
- **Selenium** - Browser automation
- **OpenAI GPT-4o-mini** - AI categorization
- **Supabase** - PostgreSQL database

### API
- **Vercel Serverless** - TypeScript functions
- **Node.js** - Runtime

### Deployment
- **Vercel** - Frontend + API hosting
- **GitHub** - Version control + CI/CD
- **Supabase** - Managed PostgreSQL

---

## 🔐 Security

- ✅ Environment variables in `.env` (not committed)
- ✅ Service keys stored in Vercel
- ✅ API routes protected with CORS
- ✅ Facebook login via browser profile

---

## 📈 Roadmap

- [ ] Add more job categories
- [ ] Support multiple languages
- [ ] Add price extraction from posts
- [ ] Create mobile app
- [ ] Add SMS notifications
- [ ] Support more social platforms (LinkedIn, Twitter)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

---

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

---

## 🙋 Support

- 📖 [Documentation](docs/)
- 🐛 [Report Bug](https://github.com/vladlevitin/work_notfier/issues)
- 💡 [Request Feature](https://github.com/vladlevitin/work_notfier/issues)

---

## ⭐ Star this repo if it helped you!

**Made with ❤️ for job seekers in Norway** 🇳🇴
