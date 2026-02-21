# 🌪️ Zephyr - Job Application Tracker

Automated job tracking with LinkedIn scraping, built with FastAPI and Supabase.

## ✨ Features

- 🔐 **Secure Authentication** - Supabase-powered user accounts
- 🌐 **Persistent Sessions** - Stay logged in across page refreshes
- 🤖 **Automated Scraping** - LinkedIn job scraper with Playwright
- 📊 **Analytics Dashboard** - Track applications, stats, and activity
- 🔍 **Custom Searches** - Define keywords, locations, and filters
- 👥 **Multi-User** - Each user has their own private dashboard
- 🎨 **Modern UI** - Responsive Bootstrap 5 design

## 🚀 Quick Start

### 1. Clone & Setup

```bash
git clone <your-repo>
cd zephyr
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Install Playwright Browsers

```bash
playwright install chromium
```

### 3. Configure Environment

Create `.env` file with your Supabase credentials:

```env
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_key
SECRET_KEY=your-secret-key-for-sessions
```

### 4. Run the Application

**Easy way:**
```bash
./start.sh
```

**Manual way:**
```bash
python run.py
```

Visit: **http://localhost:8000**

## 📁 Project Structure

```
zephyr/
├── app/
│   ├── main.py              # FastAPI application
│   ├── auth.py              # Authentication logic
│   ├── routes/              # Route handlers
│   │   ├── auth.py          # Login/signup/logout
│   │   ├── dashboard.py     # Main dashboard
│   │   ├── jobs.py          # Job listings
│   │   └── search.py        # Search configurations
│   ├── templates/           # Jinja2 HTML templates
│   └── static/              # CSS, JS, images
├── scraper.py               # LinkedIn job scraper
├── run.py                   # Application starter
├── start.sh                 # Quick start script
├── requirements.txt         # Python dependencies
└── .env                     # Configuration (not in git)
```

## 🔧 Usage

### Running the Web App

```bash
./start.sh
```

Then open http://localhost:8000 in your browser.

### Running the Scraper

The scraper runs automatically via GitHub Actions every 6 hours, or run it manually:

```bash
python scraper.py
```

### Managing Search Configs

1. Log in to the web app
2. Navigate to "Search Configs"
3. Add your search criteria (keywords, location, etc.)
4. Toggle active/inactive as needed

The scraper only runs for active configurations.

## 🏗️ Architecture

- **Frontend**: Jinja2 templates + Bootstrap 5
- **Backend**: FastAPI (Python async framework)
- **Database**: Supabase (PostgreSQL)
- **Auth**: Supabase Auth with session cookies
- **Scraper**: Playwright (headless browser)

## 🚢 Deployment

### Render.com (Recommended)

1. Connect your GitHub repository
2. Create a new Web Service
3. Build command: `pip install -r requirements.txt && playwright install chromium`
4. Start command: `python run.py`
5. Add environment variables

### Railway.app

1. Connect repository
2. Add environment variables
3. Railway auto-deploys

### Fly.io

1. `flyctl launch`
2. `flyctl secrets set SUPABASE_URL=...`
3. `flyctl deploy`

## 🛡️ Security

- ✅ Environment variables for secrets
- ✅ Supabase Row Level Security (RLS)
- ✅ Session-based authentication
- ✅ Input validation

## 📝 To-Do

- [ ] Job application automation
- [ ] More job boards (Indeed, Glassdoor)
- [ ] Email notifications
- [ ] Export to CSV/PDF
- [ ] Chrome extension for one-click apply
- [ ] Advanced filtering and sorting
- [ ] Application status tracking

---

Built with ❤️ using FastAPI, Supabase, and Playwright
 
Peepee