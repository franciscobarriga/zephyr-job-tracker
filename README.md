# 🌪️ Zephyr - Multi-User Job Tracker (Supabase Version)

Automated job application tracker with user authentication and personalized job searches.

## 🎯 What's New in V2

✅ **Multi-user support** - Each user has their own account and job list
✅ **Custom searches** - Users define their own keywords, locations, filters
✅ **Authentication** - Secure login with email/password
✅ **Row-level security** - Users only see their own jobs
✅ **Automated scraping** - Runs every 6 hours for ALL active users
✅ **Scalable** - PostgreSQL backend (Supabase)

## 🏗️ Architecture

```
Frontend:  Streamlit (with Supabase Auth)
Database:  Supabase PostgreSQL
Scraper:   GitHub Actions (runs every 6 hours)
```

## 🚀 Deployment Steps

### 1. GitHub Secrets (DONE ✅)

Already added:
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_KEY`

### 2. Update Your Repository

Replace these files in your repo:

**Core files:**
- `scraper_supabase.py` → Rename to `scraper.py`
- `streamlit_app_supabase.py` → Rename to `streamlit_app.py`
- `requirements_streamlit_only.txt` → Rename to `requirements.txt`

**New files:**
- `.github/workflows/scrape-jobs.yml`
- `.streamlit/secrets.toml` (from template)

### 3. Deploy to Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io)
2. Connect your repo: `franciscobarriga/zephyr-job-tracker`
3. Main file: `streamlit_app.py`
4. Add secrets:
   ```toml
   SUPABASE_URL = "https://ucpuvyzwlefaxieypnet.supabase.co"
   SUPABASE_ANON_KEY = "your-anon-key-from-supabase"
   ```
5. Deploy!

### 4. Test the Scraper

Manually trigger GitHub Action:
1. Go to: Actions tab in GitHub
2. Click "Zephyr Multi-User Job Scraper"
3. Click "Run workflow"
4. Watch the logs

## 📊 How It Works

### For Users:
1. **Sign up** → Create account with email/password
2. **Add searches** → Define keywords, location, remote preference
3. **Wait** → Scraper runs every 6 hours automatically
4. **Track** → Jobs appear in your dashboard, update status

### Backend:
1. **Scraper runs** → GitHub Actions every 6 hours
2. **Fetches configs** → Gets all active search_configs from Supabase
3. **Scrapes LinkedIn** → For each user's keywords
4. **Saves jobs** → To Supabase with user_id (multi-tenant isolation)
5. **Deduplicates** → Unique constraint on (user_id, job_id)

## 🔒 Security

- **Row Level Security (RLS)** enabled - users can't see others' data
- **anon key** for frontend (limited permissions)
- **service_role key** for backend scraper (full access)
- **GitHub Secrets** for credentials (encrypted)

## 📈 Scaling

Current limits:
- **Supabase Free:** 500MB DB, 50k users, 2GB bandwidth/month
- **GitHub Actions Free:** 2000 minutes/month
- **Streamlit Free:** Unlimited public apps

Typical usage:
- 100 users × 2 searches × 50 jobs = 10k rows (~5MB)
- Scraper: 10 min/run × 4 runs/day = 1200 min/month

## 💡 Usage Tips

**For you:**
- Share the Streamlit URL with friends
- They create their own accounts
- Each manages their own searches

**For your friends:**
1. Go to Streamlit URL
2. Click "Sign Up"
3. Verify email
4. Login
5. Add job searches
6. Check back in 6 hours!

## 🐛 Troubleshooting

**"Email not confirmed"**
- Check inbox/spam for Supabase confirmation email
- Resend from Supabase dashboard

**"No jobs appearing"**
- Check GitHub Actions logs for errors
- Verify search_configs.is_active = true
- LinkedIn might be rate limiting (add delays)

**"Permission denied"**
- RLS is working! User can only access their own data
- Check user_id matches in database

## 🎨 Customization

**Change scraper frequency:**
Edit `.github/workflows/scrape-jobs.yml`:
```yaml
schedule:
  - cron: '0 */6 * * *'  # Every 6 hours
  # - cron: '0 8 * * *'  # Daily at 8 AM
```

**Add OAuth login (Google/GitHub):**
Supabase dashboard → Authentication → Providers → Enable

**Custom job filters:**
Add columns to `search_configs` table and update scraper logic

## 📦 Files Explained

| File | Purpose |
|------|---------|
| `scraper_supabase.py` | Multi-user backend scraper |
| `streamlit_app_supabase.py` | Frontend with auth |
| `requirements_streamlit_only.txt` | Minimal deps for frontend |
| `.github/workflows/scrape-jobs.yml` | Automated scraping |
| `.streamlit/secrets.toml` | Supabase credentials |

## 🚀 Next Steps

**Phase 3 enhancements:**
- Email notifications for new jobs
- Job matching score (ML)
- Resume templates
- Application tracking (emails sent)
- Analytics dashboard
- Premium tier (faster scraping)

---

Built with ❤️ in Madrid
