# 🌪️ Zephyr - Complete Project Context

## 📖 What Is This Project?

**Zephyr is a web application** - think of it like LinkedIn, but for tracking YOUR job applications automatically.

### The Simple Explanation:

**Right now:** You're running a **local web server** on your computer. It's like having a mini-website running just for you at `http://localhost:8000`. Only you can see it because it's on YOUR computer.

**To share with friends:** You need to **deploy it** (put it on the internet). Then you get a real URL like `https://zephyr-tracker.onrender.com` that anyone can visit!

### Think of it like this:
- **Your computer = Your house** 🏠
  - `localhost:8000` = Only you can visit (you're inside your house)
  
- **Cloud deployment = Opening a restaurant** 🍽️
  - `https://yourapp.com` = Everyone can visit (public website)

---

## 🎯 Project Purpose

**Problem:** Job hunting sucks! You apply to 100+ jobs, forget which ones, lose track of links, miss follow-ups.

**Solution:** Zephyr automatically:
1. ✅ Scrapes LinkedIn for jobs matching your criteria
2. ✅ Saves them to YOUR private database
3. ✅ Shows them in a nice dashboard
4. ✅ Tracks your application status
5. ✅ (Future) Auto-applies to jobs for you!

---

## 🏗️ Technical Architecture

### Current Stack (FastAPI Version)

```
┌─────────────────────────────────────────────────┐
│  YOU (Browser) → http://localhost:8000          │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│  FastAPI Server (Python)                        │
│  - Handles login/signup                         │
│  - Shows dashboard                              │
│  - Manages job listings                         │
│  - Session cookies (stay logged in!)           │
└──────────────────┬──────────────────────────────┘
                   │
                   ↓
┌─────────────────────────────────────────────────┐
│  Supabase (Cloud Database)                      │
│  - Stores your jobs                             │
│  - Stores user accounts                         │
│  - Handles authentication                       │
└─────────────────────────────────────────────────┘
                   ↑
                   │
┌──────────────────┴──────────────────────────────┐
│  Scraper (Python Script)                        │
│  - Runs every 6 hours via GitHub Actions        │
│  - Scrapes LinkedIn using Playwright            │
│  - Saves new jobs to database                   │
└─────────────────────────────────────────────────┘
```

---

## 📁 Project Structure

```
zephyr/
├── app/                          # FastAPI application
│   ├── main.py                   # App entry point, routes setup
│   ├── auth.py                   # Supabase auth & user logic
│   ├── routes/                   # All route handlers
│   │   ├── auth.py               # Login, signup, logout
│   │   ├── dashboard.py          # Main dashboard with stats
│   │   ├── jobs.py               # Job listings page
│   │   └── search.py             # Search configurations
│   ├── templates/                # HTML pages (Jinja2)
│   │   ├── base.html             # Base template
│   │   ├── login.html            # Login page
│   │   ├── signup.html           # Signup page
│   │   ├── dashboard.html        # Dashboard
│   │   ├── jobs.html             # Jobs list
│   │   └── search_configs.html   # Search config manager
│   └── static/                   # CSS, JS, images
│       └── main.css              # Custom styles
│
├── scraper.py                    # LinkedIn job scraper
├── run.py                        # Server launcher
├── start.sh                      # Quick start script
├── requirements.txt              # Python dependencies
├── .env                          # Your secrets (NOT in git)
├── .gitignore                    # What to ignore in git
├── README.md                     # Documentation
└── venv/                         # Virtual environment
```

---

## 🔑 Key Files Explained

### `app/main.py`
- The "brain" of your web app
- Sets up FastAPI, routes, templates
- Handles incoming HTTP requests

### `app/auth.py`
- Connects to Supabase
- Manages user login/logout
- Checks if user is authenticated

### `app/routes/*.py`
- Each file handles one section of your site
- `auth.py` = login/signup pages
- `dashboard.py` = main dashboard
- `jobs.py` = job listings
- `search.py` = search configuration

### `app/templates/*.html`
- The actual web pages users see
- Uses Jinja2 (like Python inside HTML)
- Bootstrap 5 for styling

### `scraper.py`
- Headless browser automation (Playwright)
- Goes to LinkedIn job search
- Scrapes job title, company, location, URL
- Saves to Supabase (deduplicates by job hash)

### `run.py`
- Simple script to start the server
- Checks environment variables
- Launches uvicorn (the web server)

### `.env`
- Your secret keys and credentials
- NEVER commit this to git!
- Contains Supabase keys

---

## 🗄️ Database Schema (Supabase)

### Table: `profiles`
```sql
- id: UUID (links to auth.users)
- username: TEXT
- full_name: TEXT
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

### Table: `search_configs`
```sql
- id: SERIAL PRIMARY KEY
- user_id: UUID (foreign key)
- keywords: TEXT (e.g., "Data Analyst")
- location: TEXT (e.g., "Remote")
- is_remote: BOOLEAN
- experience_level: TEXT
- pages: INTEGER (how many pages to scrape)
- is_active: BOOLEAN (scraper only runs active ones)
- created_at: TIMESTAMP
```

### Table: `jobs`
```sql
- id: SERIAL PRIMARY KEY
- user_id: UUID (foreign key)
- title: TEXT (e.g., "Senior Data Engineer")
- company: TEXT (e.g., "Google")
- location: TEXT (e.g., "Mountain View, CA")
- url: TEXT (LinkedIn job link)
- job_hash: TEXT (unique identifier, prevents duplicates)
- source: TEXT (always "linkedin" for now)
- status: TEXT (NULL/"Applied"/"Rejected"/etc.)
- created_at: TIMESTAMP
```

**Important:** Row Level Security (RLS) ensures users only see their own data!

---

## 🚀 How to Use

### Development (Local Testing)

1. **Start the server:**
   ```bash
   cd /Users/panchis/Documents/Zephyr/zephyr
   python3 run.py
   ```

2. **Open in browser:**
   ```
   http://localhost:8000
   ```

3. **Sign up / Login**
   - Create account
   - Add search configs
   - See your dashboard

4. **Run scraper manually:**
   ```bash
   python3 scraper.py
   ```

### Production (Share with Friends)

To make it a **real website** that friends can access:

1. **Choose a hosting platform:**
   - **Render.com** (Recommended - Free tier)
   - **Railway.app** (Easy deployment)
   - **Fly.io** (Fast, edge deployment)

2. **Deploy steps (Render example):**
   ```
   1. Go to render.com
   2. Create account
   3. "New Web Service"
   4. Connect your GitHub repo
   5. Build command: pip install -r requirements.txt && playwright install chromium
   6. Start command: python run.py
   7. Add environment variables from .env
   8. Deploy!
   ```

3. **You'll get a URL like:**
   ```
   https://zephyr-tracker.onrender.com
   ```

4. **Share that URL with friends!** They can:
   - Sign up for their own account
   - Add their search preferences
   - See jobs scraped just for them

---

## 🔐 Security & Environment

### Required Environment Variables (.env file)

```env
# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUz...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUz...

# Session Security
SECRET_KEY=your-random-secret-key-here
```

### Security Features:
- ✅ Passwords hashed by Supabase
- ✅ Session cookies (encrypted)
- ✅ Row Level Security (users can't see others' data)
- ✅ Environment variables (secrets not in code)

---

## 🤖 Scraper Details

### How It Works:
1. Runs every 6 hours via GitHub Actions
2. Queries database for all active search configs
3. For each config:
   - Opens LinkedIn job search (headless browser)
   - Scrapes job cards (title, company, location, URL)
   - Generates unique hash for each job
   - Checks if job already exists in database
   - Inserts only NEW jobs
4. Logs results

### LinkedIn Scraping Challenges:
- ⚠️ No authentication = public job listings only
- ⚠️ Rate limiting = scrapes slowly (2 sec delays)
- ⚠️ HTML changes = selectors may break
- ✅ Using Playwright = more reliable than requests
- ✅ Headless browser = acts like real user

---

## 📊 User Flow

### New User Journey:
```
1. Visit site → Login page
2. Click "Sign up"
3. Enter email, username, password
4. (Email verification if configured)
5. Login
6. Redirected to Dashboard (empty, no jobs yet)
7. Click "Search Configs"
8. Add search: "Software Engineer", "Remote", 2 pages
9. Toggle "Active"
10. Wait for next scraper run (or run manually)
11. Jobs appear in dashboard!
12. Click "Applications" to see all jobs
13. Click job URL to apply on LinkedIn
```

### Returning User:
```
1. Visit site
2. Already logged in (session cookie!)
3. See updated dashboard with new jobs
4. Manage search configs
5. View applications
```

---

## 🎨 UI Framework

- **Backend**: FastAPI (Python)
- **Frontend**: Jinja2 templates + Bootstrap 5
- **Icons**: Bootstrap Icons
- **Styling**: Custom CSS + Bootstrap utilities

### Key Design Features:
- 📱 Responsive (works on mobile)
- 🎨 Gradient stat cards
- 📊 Clean tables with hover effects
- 🔔 Alert messages (success/error)
- 🚀 Fast page loads

---

## 🔄 Development Workflow

### Making Changes:

1. **Edit code:**
   ```bash
   # Templates (HTML)
   vim app/templates/dashboard.html
   
   # Routes (Python)
   vim app/routes/dashboard.py
   
   # Styles (CSS)
   vim app/static/main.css
   ```

2. **Server auto-reloads** (if running with `reload=True`)
   - Just refresh browser to see changes!

3. **Test locally** at http://localhost:8000

4. **Commit to git:**
   ```bash
   git add .
   git commit -m "Add feature X"
   git push
   ```

5. **Deploy** (if on Render/Railway, auto-deploys from git)

---

## 🐛 Common Issues & Solutions

### Issue: "Can't connect to database"
**Solution:** Check `.env` file has correct Supabase credentials

### Issue: "Page not found" or 404
**Solution:** Make sure server is running (`python3 run.py`)

### Issue: "Module not found"
**Solution:** Install dependencies: `pip install -r requirements.txt`

### Issue: "Scraper finds no jobs"
**Solution:** 
- Check internet connection
- Verify search config is active
- LinkedIn may be rate-limiting (wait a bit)

### Issue: "Logged out on refresh" (OLD - Fixed!)
**Solution:** This was the Streamlit problem. FastAPI uses cookies, so you stay logged in!

---

## 📈 Future Enhancements (TODO)

- [ ] **Auto-apply to jobs** (the ultimate goal!)
- [ ] **More job boards** (Indeed, Glassdoor, etc.)
- [ ] **Email notifications** for new jobs
- [ ] **Advanced filters** (salary, company size, etc.)
- [ ] **Application tracking** (Applied → Interview → Offer)
- [ ] **Resume parsing & matching**
- [ ] **Chrome extension** for one-click apply
- [ ] **Job alerts** via SMS/Slack
- [ ] **Analytics** (response rates, best keywords)

---

## 🆘 Need Help?

### Resources:
- **FastAPI Docs**: https://fastapi.tiangolo.com
- **Supabase Docs**: https://supabase.com/docs
- **Playwright Docs**: https://playwright.dev/python
- **Bootstrap Docs**: https://getbootstrap.com

### Commands Cheat Sheet:
```bash
# Start server
python3 run.py

# Run scraper
python3 scraper.py

# Install deps
pip install -r requirements.txt

# Create venv
python3 -m venv venv
source venv/bin/activate  # or: . venv/bin/activate

# Git commands
git status
git add .
git commit -m "message"
git push
```

---

## 🎯 Key Concepts to Remember

1. **It IS a real webpage** - just running on your computer right now
2. **localhost = only you** - deploy to share with others
3. **FastAPI = web framework** - like Flask or Django, but faster
4. **Supabase = cloud database** - PostgreSQL + auth + APIs
5. **Playwright = browser automation** - for scraping
6. **GitHub = version control** - saves your code history
7. **Deploy = put on internet** - then anyone can access it

---

**Created:** February 15, 2026  
**Status:** ✅ Fully functional FastAPI application  
**Next:** Deploy to production for public access!

