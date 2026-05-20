"""
Greenhouse public jobs API scraper.

Greenhouse has no global search, so we sweep a curated list of well-known
companies that host their careers page on Greenhouse and filter by keyword.
Endpoint: https://boards-api.greenhouse.io/v1/boards/{company}/jobs?content=true
"""

import hashlib
import re
import httpx

_API = "https://boards-api.greenhouse.io/v1/boards/{company}/jobs"

# Companies hosting on Greenhouse. Extend freely.
COMPANY_SLUGS = [
    "stripe", "airbnb", "figma", "notion", "databricks",
    "robinhood", "doordash", "coinbase", "instacart", "dropbox",
    "asana", "gitlab", "cloudflare", "twitch", "discord",
]

_TAG_RE = re.compile(r"<[^>]+>")


def _job_hash(title: str, company: str, location: str) -> str:
    return hashlib.sha256(f"{title}_{company}_{location}".lower().encode()).hexdigest()


def _strip_html(raw: str) -> str:
    """Greenhouse returns HTML-escaped content. Crude but sufficient cleanup."""
    if not raw:
        return ""
    text = (raw.replace("&lt;", "<").replace("&gt;", ">")
               .replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
               .replace("&nbsp;", " "))
    text = _TAG_RE.sub("", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


async def scrape_company(company_slug: str, keywords: str) -> list[dict]:
    """Fetch one Greenhouse board and keep jobs whose title matches the keyword."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_API.format(company=company_slug), params={"content": "true"})
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    kw = keywords.lower().strip()
    display_company = company_slug.replace("-", " ").title()
    jobs = []
    for item in data.get("jobs", []):
        title = (item.get("title") or "").strip()
        if not title or kw not in title.lower():
            continue
        job_url = (item.get("absolute_url") or "").strip()
        if not job_url:
            continue
        loc = ((item.get("location") or {}).get("name") or "").strip()
        jobs.append({
            "title": title,
            "company": display_company,
            "location": loc,
            "url": job_url,
            "description": _strip_html(item.get("content", "")),
            "job_hash": _job_hash(title, display_company, loc),
            "source": "greenhouse",
            "work_type": "Remote" if "remote" in loc.lower() else None,
        })
    return jobs


async def scrape(keywords: str, location: str = "", pages: int = 1) -> list[dict]:
    """Sweep every curated Greenhouse company. location/pages are ignored."""
    all_jobs: list[dict] = []
    for slug in COMPANY_SLUGS:
        all_jobs.extend(await scrape_company(slug, keywords))
    return all_jobs
