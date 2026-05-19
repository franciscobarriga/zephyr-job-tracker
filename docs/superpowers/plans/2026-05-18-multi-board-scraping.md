# Multi-Board Scraping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Prerequisite:** Plan `2026-05-18-resume-ai-foundation.md` must be complete. `scraper.py` must already use `app.utils.ai_client`.

**Goal:** Extend the scraper to pull jobs from Indeed (via SerpAPI) and Greenhouse/Lever (direct API) in addition to LinkedIn, with a unified deduplication and storage interface.

**Architecture:** Extract a `scrapers/` package where each board is its own module implementing a common `scrape(keywords, location, pages) -> list[dict]` interface. The main `scraper.py` orchestrates all boards per search config. SerpAPI is used for Indeed (no official API; SerpAPI is reliable). Greenhouse and Lever have public job APIs that don't require authentication.

**Tech Stack:** SerpAPI (`google-search-results` package), `httpx` (already installed) for Greenhouse/Lever REST APIs, existing Playwright for LinkedIn, pytest + respx (HTTP mocking for httpx).

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `scrapers/__init__.py` | Package marker + `scrape_all()` orchestrator |
| Create | `scrapers/linkedin.py` | LinkedIn Playwright scraper (extracted from scraper.py) |
| Create | `scrapers/indeed.py` | Indeed via SerpAPI REST |
| Create | `scrapers/greenhouse.py` | Greenhouse public jobs API |
| Create | `scrapers/lever.py` | Lever public postings API |
| Modify | `scraper.py` | Use `scrapers.scrape_all()` instead of inline LinkedIn call |
| Modify | `requirements.txt` | Add google-search-results, respx |
| Modify | `app/routes/search.py` | Add board selection checkboxes to search config |
| Create | `tests/test_scrapers_indeed.py` | Unit tests for Indeed scraper |
| Create | `tests/test_scrapers_greenhouse.py` | Unit tests for Greenhouse scraper |
| Create | `tests/test_scrapers_lever.py` | Unit tests for Lever scraper |

---

## Task 1: Dependencies + DB Migration

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add new deps to `requirements.txt`**

```
google-search-results>=2.4.2
respx>=0.21.0
```

- [ ] **Step 2: Install**

```bash
source venv/bin/activate
pip install "google-search-results>=2.4.2" "respx>=0.21.0"
```

- [ ] **Step 3: DB migration — add board selection to search_configs**

In Supabase SQL editor:

```sql
-- Which boards to scrape per search config
ALTER TABLE search_configs
  ADD COLUMN IF NOT EXISTS boards TEXT[] DEFAULT ARRAY['linkedin'];

-- Track source board more precisely (already exists as TEXT, just documenting values)
-- jobs.source values: 'linkedin' | 'indeed' | 'greenhouse' | 'lever'
```

- [ ] **Step 4: Add SERPAPI_KEY to .env**

```
SERPAPI_KEY=your-serpapi-api-key
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt
git commit -m "feat: add serpapi + respx deps; DB column for board selection"
```

---

## Task 2: Extract LinkedIn Scraper into `scrapers/` Package

**Files:**
- Create: `scrapers/__init__.py`
- Create: `scrapers/linkedin.py`
- Modify: `scraper.py`

- [ ] **Step 1: Create `scrapers/__init__.py`**

```python
from scrapers.linkedin import scrape as scrape_linkedin
from scrapers.indeed import scrape as scrape_indeed
from scrapers.greenhouse import scrape as scrape_greenhouse
from scrapers.lever import scrape as scrape_lever

_BOARD_MAP = {
    "linkedin": scrape_linkedin,
    "indeed": scrape_indeed,
    "greenhouse": scrape_greenhouse,
    "lever": scrape_lever,
}


async def scrape_all(keywords: str, location: str, pages: int, boards: list[str]) -> list[dict]:
    """Run all requested board scrapers and merge results."""
    all_jobs = []
    for board in boards:
        fn = _BOARD_MAP.get(board)
        if not fn:
            continue
        try:
            jobs = await fn(keywords, location, pages)
            for j in jobs:
                j["source"] = board
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"  ⚠️  Board '{board}' failed: {e}")
    return all_jobs
```

- [ ] **Step 2: Create `scrapers/linkedin.py`**

Move the `scrape_linkedin_jobs` function from `scraper.py` into this file, renaming it `scrape`:

```python
"""LinkedIn job scraper using Playwright."""
import asyncio
import hashlib
import random
import re
from urllib.parse import quote_plus
from playwright.async_api import async_playwright


MIN_DELAY, MAX_DELAY = 1.0, 4.0
MIN_SCROLL, MAX_SCROLL = 100, 400


async def _human_delay(min_s=None, max_s=None):
    await asyncio.sleep(random.uniform(min_s or MIN_DELAY, max_s or MAX_DELAY))


async def _human_scroll(page):
    for _ in range(random.randint(3, 6)):
        await page.mouse.wheel(0, random.randint(MIN_SCROLL, MAX_SCROLL))
        await asyncio.sleep(random.uniform(0.5, 1.5))


def _random_ua():
    return random.choice([
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ])


def _random_vp():
    return random.choice([
        {'width': 1280, 'height': 800},
        {'width': 1440, 'height': 900},
        {'width': 1920, 'height': 1080},
    ])


def _job_hash(title, company, location):
    return hashlib.sha256(f"{title}_{company}_{location}".lower().encode()).hexdigest()


def _extract_work_type(text):
    t = (text or "").lower()
    if "remote" in t: return "Remote"
    if "hybrid" in t: return "Hybrid"
    if "onsite" in t or "on-site" in t: return "On-site"
    return None


async def scrape(keywords: str, location: str, pages: int = 1) -> list[dict]:
    jobs = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent=_random_ua(),
            viewport=_random_vp(),
            locale="en-US",
            timezone_id="America/New_York",
        )
        await context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
        )
        page = await context.new_page()

        for page_num in range(pages):
            url = (
                f"https://www.linkedin.com/jobs/search/?"
                f"keywords={quote_plus(keywords)}&location={quote_plus(location)}&start={page_num * 25}"
            )
            try:
                await _human_delay(1, 3)
                await page.goto(url, wait_until="networkidle", timeout=45000)
                await _human_scroll(page)
                await page.wait_for_selector(".job-search-card", timeout=15000)

                for card in await page.query_selector_all(".job-search-card"):
                    try:
                        title = (await (await card.query_selector(".base-search-card__title")).inner_text()).strip()
                        company = (await (await card.query_selector(".base-search-card__subtitle")).inner_text()).strip()
                        loc = (await (await card.query_selector(".job-search-card__location")).inner_text()).strip()
                        link = await (await card.query_selector("a.base-card__full-link")).get_attribute("href")
                        job_url = link.split("?")[0] if link else None
                        jobs.append({
                            "title": title, "company": company, "location": loc,
                            "url": job_url, "job_hash": _job_hash(title, company, loc),
                            "work_type": _extract_work_type(loc),
                        })
                    except Exception:
                        continue
                await _human_delay(2, 5)
            except Exception as e:
                print(f"  ❌ LinkedIn page {page_num + 1}: {e}")
        await browser.close()
    return jobs
```

- [ ] **Step 3: Update `scraper.py` to use `scrapers.scrape_all()`**

Replace the call to `scrape_linkedin_jobs(...)` in `scrape_for_user()` with:

```python
from scrapers import scrape_all

# In scrape_for_user():
boards = config.get("boards") or ["linkedin"]
jobs = await scrape_all(config["keywords"], config["location"], config["pages"], boards)
```

Remove the old `scrape_linkedin_jobs` function from `scraper.py` — it now lives in `scrapers/linkedin.py`.

- [ ] **Step 4: Verify scraper still works**

```bash
python -c "import scraper; print('OK')"
```

Expected: `OK`.

- [ ] **Step 5: Commit**

```bash
git add scrapers/__init__.py scrapers/linkedin.py scraper.py
git commit -m "refactor: extract LinkedIn scraper into scrapers/ package"
```

---

## Task 3: Indeed Scraper (SerpAPI)

**Files:**
- Create: `scrapers/indeed.py`
- Create: `tests/test_scrapers_indeed.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_scrapers_indeed.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


class TestIndeedScrape:
    @pytest.mark.asyncio
    async def test_returns_jobs_from_serpapi_response(self):
        mock_results = {
            "jobs_results": [
                {
                    "title": "Data Engineer",
                    "company_name": "Stripe",
                    "location": "Remote",
                    "job_highlights": [],
                    "related_links": [{"link": "https://indeed.com/job/123"}],
                }
            ]
        }
        with patch("scrapers.indeed.GoogleSearch") as mock_gs:
            mock_gs.return_value.get_dict.return_value = mock_results
            from scrapers.indeed import scrape
            jobs = await scrape("Data Engineer", "Remote", pages=1)

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Data Engineer"
        assert jobs[0]["company"] == "Stripe"
        assert jobs[0]["url"] == "https://indeed.com/job/123"

    @pytest.mark.asyncio
    async def test_returns_empty_list_when_no_results(self):
        with patch("scrapers.indeed.GoogleSearch") as mock_gs:
            mock_gs.return_value.get_dict.return_value = {}
            from scrapers.indeed import scrape
            jobs = await scrape("Nonexistent role", "Mars", pages=1)

        assert jobs == []

    @pytest.mark.asyncio
    async def test_skips_jobs_with_no_url(self):
        mock_results = {
            "jobs_results": [
                {"title": "Engineer", "company_name": "Corp", "location": "NY",
                 "related_links": []},  # no link
            ]
        }
        with patch("scrapers.indeed.GoogleSearch") as mock_gs:
            mock_gs.return_value.get_dict.return_value = mock_results
            from scrapers.indeed import scrape
            jobs = await scrape("Engineer", "NY", pages=1)

        assert jobs == []
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_scrapers_indeed.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `scrapers/indeed.py`**

```python
"""Indeed job scraper via SerpAPI."""
import hashlib
import os
from serpapi import GoogleSearch

_SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")


def _job_hash(title, company, location):
    return hashlib.sha256(f"{title}_{company}_{location}".lower().encode()).hexdigest()


async def scrape(keywords: str, location: str, pages: int = 1) -> list[dict]:
    jobs = []
    for page_num in range(pages):
        params = {
            "engine": "google_jobs",
            "q": f"{keywords} {location}",
            "start": page_num * 10,
            "api_key": _SERPAPI_KEY,
        }
        results = GoogleSearch(params).get_dict()
        for item in results.get("jobs_results", []):
            links = item.get("related_links", [])
            url = links[0]["link"] if links else None
            if not url:
                continue
            title = item.get("title", "").strip()
            company = item.get("company_name", "").strip()
            loc = item.get("location", "").strip()
            jobs.append({
                "title": title,
                "company": company,
                "location": loc,
                "url": url,
                "job_hash": _job_hash(title, company, loc),
                "work_type": "Remote" if "remote" in loc.lower() else None,
            })
    return jobs
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scrapers_indeed.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/indeed.py tests/test_scrapers_indeed.py
git commit -m "feat: Indeed scraper via SerpAPI"
```

---

## Task 4: Greenhouse Scraper

**Files:**
- Create: `scrapers/greenhouse.py`
- Create: `tests/test_scrapers_greenhouse.py`

Greenhouse has a public API: `https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true`

- [ ] **Step 1: Write failing tests**

Create `tests/test_scrapers_greenhouse.py`:

```python
import pytest
import respx
import httpx


class TestGreenhouseScrape:
    @pytest.mark.asyncio
    async def test_fetches_jobs_for_known_company(self):
        mock_response = {
            "jobs": [
                {
                    "title": "Backend Engineer",
                    "location": {"name": "San Francisco, CA"},
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/123",
                    "content": "<p>We build payments infrastructure...</p>",
                }
            ]
        }
        with respx.mock:
            respx.get("https://boards-api.greenhouse.io/v1/boards/stripe/jobs").mock(
                return_value=httpx.Response(200, json=mock_response)
            )
            from scrapers.greenhouse import scrape_company
            jobs = await scrape_company("stripe", "Backend Engineer")

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Backend Engineer"
        assert jobs[0]["company"] == "stripe"

    @pytest.mark.asyncio
    async def test_returns_empty_on_404(self):
        with respx.mock:
            respx.get("https://boards-api.greenhouse.io/v1/boards/unknown-co/jobs").mock(
                return_value=httpx.Response(404)
            )
            from scrapers.greenhouse import scrape_company
            jobs = await scrape_company("unknown-co", "Engineer")

        assert jobs == []

    @pytest.mark.asyncio
    async def test_filters_by_keywords(self):
        mock_response = {
            "jobs": [
                {"title": "Backend Engineer", "location": {"name": "Remote"},
                 "absolute_url": "https://boards.greenhouse.io/co/jobs/1", "content": ""},
                {"title": "Marketing Manager", "location": {"name": "Remote"},
                 "absolute_url": "https://boards.greenhouse.io/co/jobs/2", "content": ""},
            ]
        }
        with respx.mock:
            respx.get("https://boards-api.greenhouse.io/v1/boards/co/jobs").mock(
                return_value=httpx.Response(200, json=mock_response)
            )
            from scrapers.greenhouse import scrape_company
            jobs = await scrape_company("co", "Backend")

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Backend Engineer"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_scrapers_greenhouse.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `scrapers/greenhouse.py`**

```python
"""Greenhouse public jobs API scraper."""
import hashlib
import httpx


_API_BASE = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"


def _job_hash(title, company, location):
    return hashlib.sha256(f"{title}_{company}_{location}".lower().encode()).hexdigest()


async def scrape_company(company_slug: str, keywords: str) -> list[dict]:
    """Fetch all jobs from a Greenhouse board and filter by keywords."""
    url = _API_BASE.format(company=company_slug)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params={"content": "true"})
        if resp.status_code != 200:
            return []

    data = resp.json()
    kw_lower = keywords.lower()
    jobs = []
    for item in data.get("jobs", []):
        title = item.get("title", "").strip()
        if kw_lower not in title.lower():
            continue
        loc = (item.get("location") or {}).get("name", "").strip()
        job_url = item.get("absolute_url", "")
        if not job_url:
            continue
        jobs.append({
            "title": title,
            "company": company_slug,
            "location": loc,
            "url": job_url,
            "description": item.get("content", ""),
            "job_hash": _job_hash(title, company_slug, loc),
            "work_type": "Remote" if "remote" in loc.lower() else None,
        })
    return jobs


async def scrape(keywords: str, location: str, pages: int = 1) -> list[dict]:
    """
    Greenhouse doesn't have a global search API.
    Scrape a curated list of top Greenhouse-hosted companies.
    Extend COMPANY_SLUGS for more coverage.
    """
    COMPANY_SLUGS = [
        "stripe", "airbnb", "figma", "notion", "linear",
        "vercel", "supabase", "github", "hashicorp", "datadog",
    ]
    all_jobs = []
    for slug in COMPANY_SLUGS:
        try:
            jobs = await scrape_company(slug, keywords)
            all_jobs.extend(jobs)
        except Exception:
            continue
    return all_jobs
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scrapers_greenhouse.py -v
```

Expected: All 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/greenhouse.py tests/test_scrapers_greenhouse.py
git commit -m "feat: Greenhouse public API scraper with keyword filtering"
```

---

## Task 5: Lever Scraper

**Files:**
- Create: `scrapers/lever.py`
- Create: `tests/test_scrapers_lever.py`

Lever's public API: `https://api.lever.co/v0/postings/{company}?mode=json`

- [ ] **Step 1: Write failing tests**

Create `tests/test_scrapers_lever.py`:

```python
import pytest
import respx
import httpx


class TestLeverScrape:
    @pytest.mark.asyncio
    async def test_fetches_and_filters_jobs(self):
        mock_response = [
            {
                "text": "Senior Backend Engineer",
                "categories": {"location": "Remote"},
                "hostedUrl": "https://jobs.lever.co/acme/abc-123",
                "descriptionPlain": "We're looking for a backend engineer...",
            },
            {
                "text": "Product Designer",
                "categories": {"location": "San Francisco"},
                "hostedUrl": "https://jobs.lever.co/acme/def-456",
                "descriptionPlain": "Design our product...",
            }
        ]
        with respx.mock:
            respx.get("https://api.lever.co/v0/postings/acme").mock(
                return_value=httpx.Response(200, json=mock_response)
            )
            from scrapers.lever import scrape_company
            jobs = await scrape_company("acme", "Backend")

        assert len(jobs) == 1
        assert jobs[0]["title"] == "Senior Backend Engineer"

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        with respx.mock:
            respx.get("https://api.lever.co/v0/postings/badco").mock(
                return_value=httpx.Response(500)
            )
            from scrapers.lever import scrape_company
            jobs = await scrape_company("badco", "Engineer")

        assert jobs == []
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_scrapers_lever.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `scrapers/lever.py`**

```python
"""Lever public postings API scraper."""
import hashlib
import httpx


_API_BASE = "https://api.lever.co/v0/postings/{company}"


def _job_hash(title, company, location):
    return hashlib.sha256(f"{title}_{company}_{location}".lower().encode()).hexdigest()


async def scrape_company(company_slug: str, keywords: str) -> list[dict]:
    url = _API_BASE.format(company=company_slug)
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params={"mode": "json"})
        if resp.status_code != 200:
            return []

    kw_lower = keywords.lower()
    jobs = []
    for item in resp.json():
        title = item.get("text", "").strip()
        if kw_lower not in title.lower():
            continue
        categories = item.get("categories") or {}
        loc = categories.get("location", "").strip()
        job_url = item.get("hostedUrl", "")
        if not job_url:
            continue
        jobs.append({
            "title": title,
            "company": company_slug,
            "location": loc,
            "url": job_url,
            "description": item.get("descriptionPlain", ""),
            "job_hash": _job_hash(title, company_slug, loc),
            "work_type": "Remote" if "remote" in loc.lower() else None,
        })
    return jobs


async def scrape(keywords: str, location: str, pages: int = 1) -> list[dict]:
    """Scrape a curated list of Lever-hosted companies. Extend COMPANY_SLUGS."""
    COMPANY_SLUGS = [
        "netflix", "shopify", "twilio", "plaid", "rippling",
        "brex", "gusto", "lattice", "retool", "segment",
    ]
    all_jobs = []
    for slug in COMPANY_SLUGS:
        try:
            jobs = await scrape_company(slug, keywords)
            all_jobs.extend(jobs)
        except Exception:
            continue
    return all_jobs
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_scrapers_lever.py -v
```

Expected: Both tests PASS.

- [ ] **Step 5: Commit**

```bash
git add scrapers/lever.py tests/test_scrapers_lever.py
git commit -m "feat: Lever public postings API scraper with keyword filtering"
```

---

## Task 6: Board Selection in Search Config UI

**Files:**
- Modify: `app/routes/search.py`
- Modify: `app/templates/search_configs.html`

- [ ] **Step 1: Update search config create/update endpoints in `app/routes/search.py`**

In the POST handler for creating a search config, add `boards` field extraction from form:

```python
@router.post("/create")
async def create_search_config(
    request: Request,
    keywords: str = Form(...),
    location: str = Form(...),
    pages: int = Form(1),
    boards: list[str] = Form(["linkedin"]),
    user=Depends(get_current_user),
):
    supabase.table("search_configs").insert({
        "user_id": user["id"],
        "keywords": keywords,
        "location": location,
        "pages": pages,
        "boards": boards,
        "is_active": True,
    }).execute()
    return RedirectResponse(url="/search", status_code=303)
```

- [ ] **Step 2: Add board checkboxes to search config form in `search_configs.html`**

Inside the search config creation form, after the `pages` field:

```html
<div class="mb-3">
    <label class="form-label">Job Boards</label>
    <div class="d-flex gap-3 flex-wrap">
        <div class="form-check">
            <input class="form-check-input" type="checkbox" name="boards" value="linkedin"
                   id="board-linkedin" checked>
            <label class="form-check-label" for="board-linkedin">
                <i class="bi bi-linkedin me-1"></i>LinkedIn
            </label>
        </div>
        <div class="form-check">
            <input class="form-check-input" type="checkbox" name="boards" value="indeed"
                   id="board-indeed">
            <label class="form-check-label" for="board-indeed">
                <i class="bi bi-briefcase me-1"></i>Indeed
            </label>
        </div>
        <div class="form-check">
            <input class="form-check-input" type="checkbox" name="boards" value="greenhouse"
                   id="board-greenhouse">
            <label class="form-check-label" for="board-greenhouse">
                <i class="bi bi-building me-1"></i>Greenhouse
            </label>
        </div>
        <div class="form-check">
            <input class="form-check-input" type="checkbox" name="boards" value="lever"
                   id="board-lever">
            <label class="form-check-label" for="board-lever">
                <i class="bi bi-toggles me-1"></i>Lever
            </label>
        </div>
    </div>
</div>
```

- [ ] **Step 3: Run full test suite**

```bash
pytest tests/ -v
```

Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add scrapers/ app/routes/search.py app/templates/search_configs.html tests/
git commit -m "feat: multi-board scraping UI — users can select LinkedIn/Indeed/Greenhouse/Lever per search"
```

---

## Self-Review

**Spec coverage:**
- ✅ LinkedIn — `scrapers/linkedin.py` (extracted from scraper.py)
- ✅ Indeed — `scrapers/indeed.py` via SerpAPI
- ✅ Greenhouse — `scrapers/greenhouse.py` via public API
- ✅ Lever — `scrapers/lever.py` via public API
- ✅ Filter by title/keywords — all scrapers filter by keyword
- ✅ User selects boards per search config — checkboxes in UI + DB column
- ✅ Unified dedup — `job_hash` in each scraper, same dedup logic in `scraper.py`

**Limitation documented:**
- Greenhouse and Lever scrapers use a curated company list, not a global search — users can extend `COMPANY_SLUGS`. This is the best available approach without authentication. ✅

**Type consistency:**
- All `scrape()` functions return `list[dict]` with keys `title, company, location, url, job_hash, work_type` ✅
- `source` field is set by `scrape_all()` orchestrator, not individual scrapers ✅
