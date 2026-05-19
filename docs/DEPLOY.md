# Deploying Zephyr

The web app is containerized — any platform that runs a `Dockerfile` works.
The scraper continues to run on **GitHub Actions** (cron), so the deployed
web app does NOT need to scrape on its own.

## Railway (recommended)

1. Sign up at https://railway.com → "New project" → "Deploy from GitHub repo".
2. Pick `franciscobarriga/zephyr-job-tracker`. Railway detects `Dockerfile` and
   `railway.toml` automatically.
3. In **Variables**, set:
   - `SUPABASE_URL`
   - `SUPABASE_ANON_KEY`
   - `SUPABASE_SERVICE_KEY`
   - `SECRET_KEY` (any random string — used for cookie signing)
   - `ANTHROPIC_API_KEY`
4. Click **Generate Domain** under Settings → Networking → you get a
   `*.up.railway.app` URL. (Custom domain optional.)
5. First build takes ~5 minutes (downloads Playwright image).

## Local docker run

```bash
docker build -t zephyr .
docker run --rm -p 8000:8000 --env-file .env zephyr
```

## What the deployed web app does (and doesn't)

- ✅ Serves the dashboard, jobs board, resume upload, search config UI
- ✅ Calls Anthropic for resume tailoring / on-demand AI features
- ✅ Reads/writes Supabase
- ❌ Does NOT run the scraper. Scraping happens in GitHub Actions
  (`.github/workflows/scraper.yml`) on a cron, writes to the same Supabase
  project. Cleanup runs separately on a daily cron.

This keeps the web container small, scraper-runs auditable in Actions logs,
and removes the headless-browser failure mode from request handling.
