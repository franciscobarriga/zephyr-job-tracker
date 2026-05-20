"""
Lever public postings API scraper.

Like Greenhouse, Lever has no global search, so we sweep a curated list of
companies hosting on Lever and filter by keyword.
Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
"""

import hashlib
import httpx

_API = "https://api.lever.co/v0/postings/{company}"

# Companies hosting on Lever. Extend freely.
COMPANY_SLUGS = [
    "netflix", "spotify", "shopify", "plaid", "ramp",
    "brex", "gusto", "lattice", "retool", "mistral",
    "anduril", "scaleai", "vercel", "huggingface", "perplexity-ai",
]


def _job_hash(title: str, company: str, location: str) -> str:
    return hashlib.sha256(f"{title}_{company}_{location}".lower().encode()).hexdigest()


async def scrape_company(company_slug: str, keywords: str) -> list[dict]:
    """Fetch one Lever board and keep jobs whose title matches the keyword."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(_API.format(company=company_slug), params={"mode": "json"})
        if resp.status_code != 200:
            return []
        data = resp.json()
    except Exception:
        return []

    kw = keywords.lower().strip()
    display_company = company_slug.replace("-", " ").title()
    jobs = []
    for item in data:
        title = (item.get("text") or "").strip()
        if not title or kw not in title.lower():
            continue
        job_url = (item.get("hostedUrl") or "").strip()
        if not job_url:
            continue
        loc = ((item.get("categories") or {}).get("location") or "").strip()
        jobs.append({
            "title": title,
            "company": display_company,
            "location": loc,
            "url": job_url,
            "description": (item.get("descriptionPlain") or "").strip(),
            "job_hash": _job_hash(title, display_company, loc),
            "source": "lever",
            "work_type": "Remote" if "remote" in loc.lower() else None,
        })
    return jobs


async def scrape(keywords: str, location: str = "", pages: int = 1) -> list[dict]:
    """Sweep every curated Lever company. location/pages are ignored."""
    all_jobs: list[dict] = []
    for slug in COMPANY_SLUGS:
        all_jobs.extend(await scrape_company(slug, keywords))
    return all_jobs
