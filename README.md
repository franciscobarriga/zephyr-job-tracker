# 🌪️ Zephyr - Automated Job Application Tracker

Automatically scrape LinkedIn jobs and track your applications with a beautiful Streamlit interface.

## Features

- 🔍 Automated LinkedIn job scraping (no login required)
- 📊 Google Sheets integration for data persistence
- 🎨 Clean Streamlit UI with filtering and search
- ⏰ Scheduled daily scraping via GitHub Actions
- 📝 Application status tracking and notes
- 📥 CSV export functionality

## Quick Start

### 1. Prerequisites

- Python 3.11+
- Google Cloud account (free tier)
- GitHub account (free tier)
- VS Code (recommended)

### 2. Setup Google Sheets

1. **Create a Google Sheet**:
   - Go to [Google Sheets](https://sheets.google.com)
   - Create a new spreadsheet named "Zephyr Jobs"
   - Add these headers in the first row:
     ```
     job_id | title | company | location | posted_date | url | keywords | scraped_date | status | notes
     ```
   - Copy the sheet URL

2. **Enable Google Sheets API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project (or select existing)
   - Enable "Google Sheets API" and "Google Drive API"

3. **Create Service Account**:
   - Go to "IAM & Admin" > "Service Accounts"
   - Click "Create Service Account"
   - Name it "zephyr-bot", give it "Editor" role
   - Click "Create Key" > JSON > Download the file
   - Open the JSON file - you'll need these values

4. **Share Sheet with Service Account**:
   - Open your Google Sheet
   - Click "Share"
   - Paste the `client_email` from the JSON file
   - Give it "Editor" access

### 3. Local Setup

1. **Install Dependencies**:
   ```bash
   cd zephyr
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Configure Secrets**:
   - Rename `.streamlit/secrets.toml.template` to `.streamlit/secrets.toml`
   - Fill in values from your Google Cloud service account JSON file
   - Update `google_sheet_url` in `config.yaml`

3. **Configure Search Parameters**:
   - Edit `config.yaml` with your desired job searches
   - Customize keywords, locations, and number of pages

4. **Test Locally**:
   ```bash
   # Test scraper
   python scraper.py

   # Run Streamlit app
   streamlit run streamlit_app.py
   ```

### 4. Deploy to Streamlit Cloud

1. **Push to GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Deploy on Streamlit**:
   - Go to [share.streamlit.io](https://share.streamlit.io)
   - Click "New app"
   - Connect your GitHub repository
   - Set main file: `streamlit_app.py`
   - Copy contents of `.streamlit/secrets.toml` to Streamlit secrets
   - Deploy!

### 5. Setup GitHub Actions (Automated Scraping)

1. **Add Repository Secrets**:
   - Go to your GitHub repo > Settings > Secrets > Actions
   - Add these secrets from your service account JSON:
     ```
     GOOGLE_SHEET_URL
     GSHEETS_TYPE
     GSHEETS_PROJECT_ID
     GSHEETS_PRIVATE_KEY_ID
     GSHEETS_PRIVATE_KEY
     GSHEETS_CLIENT_EMAIL
     GSHEETS_CLIENT_ID
     GSHEETS_CLIENT_CERT_URL
     ```

2. **Enable Workflow**:
   - Go to Actions tab
   - Enable workflows
   - Scraper runs daily at 8 AM CET automatically

3. **Manual Trigger**:
   - Go to Actions > "Zephyr Job Scraper"
   - Click "Run workflow"

## Usage

### Access Your App
- Local: `http://localhost:8501`
- Production: Your Streamlit Cloud URL

### Features
- Browse and filter job listings
- Update application status
- Add notes for each job
- Export to CSV
- Real-time updates from Google Sheets

## Configuration

### Search Parameters

Edit `config.yaml`:
```yaml
searches:
  - keywords: "machine learning engineer"
    location: "Remote"
    pages: 3  # 25 jobs per page
```

### Schedule

Edit `.github/workflows/scraper.yml`:
```yaml
schedule:
  - cron: '0 7 * * *'  # 7 AM UTC = 8 AM CET
```

## Troubleshooting

**Scraper fails**: Check GitHub Actions logs, verify secrets are correct

**Streamlit connection error**: Verify `.streamlit/secrets.toml` matches JSON

**No jobs appearing**: Check Google Sheet permissions

**Rate limiting**: Reduce pages in config.yaml

## Sharing with Friends

### Option A: Individual Deployments
1. Each friend forks your GitHub repo
2. Creates their own Google Sheet
3. Deploys their own Streamlit app

### Option B: Shared Sheet (Simple)
1. Share your Streamlit app URL
2. All use the same sheet
3. (Optional) Add user_id column to filter by user

## Cost

**$0** - Everything runs on free tiers:
- Streamlit Community Cloud (free)
- GitHub Actions (2000 mins/month free)
- Google Sheets API (free tier sufficient)

## Future Enhancements

- [ ] Email notifications
- [ ] Multi-platform scraping (Indeed, Glassdoor)
- [ ] ML-based job matching
- [ ] Resume templates
- [ ] Analytics dashboard

## License

MIT License - Feel free to modify and share!

---

Built with ❤️ for efficient job hunting
