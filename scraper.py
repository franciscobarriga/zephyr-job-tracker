"""
Zephyr Job Scraper V4 - Human-like Behavior Version
Scrapes LinkedIn with anti-detection features
"""

import os
import asyncio
import hashlib
import re
import random
import json
import requests
from datetime import datetime, timedelta
from urllib.parse import quote_plus
from dotenv import load_dotenv
from supabase import create_client, Client
from playwright.async_api import async_playwright

# Load environment variables
load_dotenv()

# Configuration
SCRAPE_DELAY = 3  # seconds between users

# Human-like behavior settings
MIN_DELAY = 1.0   # minimum delay between actions (seconds)
MAX_DELAY = 4.0   # maximum delay between actions (seconds)
MIN_SCROLL = 100   # minimum scroll distance
MAX_SCROLL = 400   # maximum scroll distance

# Initialize Supabase client
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_SERVICE_KEY")
)


# ============== Human-like Behavior Functions ==============

async def human_delay(min_seconds=None, max_seconds=None):
    """Random delay to simulate human thinking/reading time"""
    min_sec = min_seconds or MIN_DELAY
    max_sec = max_seconds or MAX_DELAY
    delay = random.uniform(min_sec, max_sec)
    await asyncio.sleep(delay)


async def human_mouse_move(page):
    """Move mouse randomly to simulate human browsing"""
    # Get viewport size
    viewport = page.viewport_size
    if not viewport:
        return

    # Do 2-4 random movements
    for _ in range(random.randint(2, 4)):
        x = random.randint(50, viewport['width'] - 50)
        y = random.randint(50, viewport['height'] - 50)

        # Move to position with random duration
        await page.mouse.move(x, y)
        await asyncio.sleep(random.uniform(0.1, 0.3))


async def human_scroll(page):
    """Scroll like a human - not smooth, with random pauses"""
    viewport = page.viewport_size
    if not viewport:
        return

    # Do multiple scroll "stops" like a human reading
    scroll_pauses = random.randint(3, 6)

    for _ in range(scroll_pauses):
        # Random mouse movement first
        await human_mouse_move(page)

        # Then scroll a random amount
        scroll_amount = random.randint(MIN_SCROLL, MAX_SCROLL)
        await page.mouse.wheel(0, scroll_amount)

        # Random pause to "read" content
        await human_delay(0.5, 1.5)


async def human_click(page, selector):
    """Click with human-like delay and movement"""
    try:
        # Move mouse to element area first
        await human_mouse_move(page)

        # Click
        await page.click(selector)
        await human_delay(0.2, 0.5)
    except Exception:
        pass  # Element might not exist, that's ok


def random_user_agent():
    """Return a random user agent string"""
    user_agents = [
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    ]
    return random.choice(user_agents)


def random_viewport():
    """Return random viewport dimensions"""
    viewports = [
        {'width': 1280, 'height': 800},
        {'width': 1366, 'height': 768},
        {'width': 1440, 'height': 900},
        {'width': 1920, 'height': 1080},
    ]
    return random.choice(viewports)


def generate_job_hash(title, company, location):
    """Generate unique hash for job deduplication"""
    unique_string = f"{title}_{company}_{location}".lower()
    return hashlib.sha256(unique_string.encode()).hexdigest()


def extract_salary(salary_text):
    """Extract min/max salary from salary text"""
    if not salary_text:
        return None, None, None

    # Pattern: $80K - $120K per year (or similar)
    # Pattern: $80,000 - $120,000 per year
    salary_pattern = r'\$?([\d,]+(?:\.\d+)?)\s*(K|k)?'
    matches = re.findall(salary_pattern, salary_text)

    currency = "USD" if "$" in salary_text else None

    if len(matches) >= 2:
        min_sal = int(matches[0][0].replace(",", ""))
        max_sal = int(matches[1][0].replace(",", ""))
        # Handle K suffix
        if matches[0][1].lower() == 'k':
            min_sal *= 1000
        if matches[1][1].lower() == 'k':
            max_sal *= 1000
        return min_sal, max_sal, currency
    elif len(matches) == 1:
        sal = int(matches[0][0].replace(",", ""))
        if matches[0][1].lower() == 'k':
            sal *= 1000
        return sal, sal, currency

    return None, None, currency


def extract_posted_date(posted_text):
    """Convert posted text to ISO date"""
    if not posted_text:
        return None

    posted_text = posted_text.lower().strip()

    # Extract number
    num_match = re.search(r'(\d+)', posted_text)
    if not num_match:
        return None

    num = int(num_match.group(1))

    # Calculate date
    if "minute" in posted_text or "hour" in posted_text:
        return datetime.now().isoformat()
    elif "day" in posted_text:
        days_ago = num
    elif "week" in posted_text:
        days_ago = num * 7
    elif "month" in posted_text:
        days_ago = num * 30
    else:
        return None

    from datetime import timedelta
    posted_date = datetime.now() - timedelta(days=days_ago)
    return posted_date.isoformat()


def extract_job_type(metadata_text):
    """Extract job type from metadata"""
    if not metadata_text:
        return None

    text = metadata_text.lower()
    if "full-time" in text:
        return "Full-time"
    elif "part-time" in text:
        return "Part-time"
    elif "contract" in text:
        return "Contract"
    elif "internship" in text:
        return "Internship"
    elif "temporary" in text:
        return "Temporary"

    return None


def extract_experience_level(metadata_text):
    """Extract experience level from metadata"""
    if not metadata_text:
        return None

    text = metadata_text.lower()
    if "entry" in text:
        return "Entry"
    elif "associate" in text:
        return "Associate"
    elif "mid-senior" in text:
        return "Mid-Senior"
    elif "senior" in text:
        return "Senior"
    elif "director" in text:
        return "Director"
    elif "executive" in text:
        return "Executive"

    return None


def extract_work_type(metadata_text):
    """Extract work type (remote, hybrid, onsite)"""
    if not metadata_text:
        return None

    text = metadata_text.lower()
    if "remote" in text:
        return "Remote"
    elif "hybrid" in text:
        return "Hybrid"
    elif "onsite" in text or "on-site" in text:
        return "On-site"

    return None


def analyze_job(description: str, retries: int = 3) -> dict:
    """Analyze job posting using Ollama LLM to extract summary and requirements"""
    if not description:
        return {"summary": "—", "requirements": ""}

    for attempt in range(retries):
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": "llama3.2:latest",
                    "prompt": f"""
Analyze this job posting and return ONLY valid JSON:
{{
    "summary": "2-3 sentences: what the company does, the role, YOE if stated",
    "requirements": ["tool1", "skill2", "technology3"]
}}

Rules:
- summary: concise, mention YOE only if explicitly stated
- requirements: only hard skills and tools, no soft skills, no labels like "(inferred)"
- requirements: return an empty list [] if no tools or hard skills can be identified

Job posting:
{description[:3000]}
""",
                    "stream": False
                },
                timeout=120
            )

            if not response.text.strip():
                print(f"  ⚠️  Empty response, retrying ({attempt + 1}/{retries})...")
                continue

            raw = response.json()["response"].strip()
            if raw.startswith("```"):
                raw = raw.split("```")[1]
                if raw.startswith("json"):
                    raw = raw[4:]
            parsed = json.loads(raw.strip())

            reqs = [r.replace("(inferred)", "").strip() for r in parsed.get("requirements", [])]
            reqs = [r for r in reqs if r]  # drop anything that was only "(inferred)"
            return {
                "summary": parsed.get("summary", "—"),
                "requirements": ", ".join(reqs) if reqs else ""
            }

        except Exception as e:
            print(f"  ⚠️  Attempt {attempt + 1} failed: {e}")
            continue

    return {"summary": "—", "requirements": ""}




async def get_job_description(page, job_url):
    """Visit job detail page and extract description"""
    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=15000)
        await asyncio.sleep(2)  # Wait for content to load

        # Try multiple selectors for job description
        description = None

        selectors = [
            ".jobs-description__content",
            ".job-view-layout .jobs-box",
            ".jobs-description__body",
            "[data-test-id='job-details']",
            ".jobs-details__main-content",
        ]

        for selector in selectors:
            elem = await page.query_selector(selector)
            if elem:
                description = await elem.inner_text()
                if description and len(description) > 50:
                    break

        if not description:
            # Fallback: get all paragraph text
            paragraphs = await page.query_selector_all("p, li")
            description_parts = []
            for p in paragraphs[:10]:  # Limit to first 10
                text = await p.inner_text()
                if text and len(text) > 20:
                    description_parts.append(text)
            description = " ".join(description_parts)

        return description[:10000] if description else None  # Limit length

    except Exception as e:
        print(f"    ⚠️  Error getting job description: {e}")
        return None


async def analyze_new_jobs(user_id, jobs_data):
    """Visit each new job URL and run AI analysis"""
    if not jobs_data:
        return

    print(f"  🤖 Running AI analysis on {len(jobs_data)} new jobs...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        analyzed = 0
        for job in jobs_data:
            try:
                # Get job description
                description = await get_job_description(page, job["url"])

                if description:
                    # Run AI analysis
                    print(f"    📝 Analyzing: {job['title'][:30]}...")
                    analysis = analyze_job(description)

                    # Update job with AI analysis
                    supabase.table("jobs").update({
                        "ai_summary": analysis.get("summary"),
                        "ai_requirements": analysis.get("requirements")
                    }).eq("id", job["id"]).execute()

                    analyzed += 1
                    await human_delay(1, 3)  # Rate limit between AI calls
                else:
                    print(f"    ⚠️  No description found for: {job['title'][:30]}")

            except Exception as e:
                print(f"    ⚠️  Error analyzing job: {e}")
                continue

        await browser.close()

    print(f"  ✅ AI analysis complete: {analyzed} jobs analyzed")

    print(f"  ✅ AI analysis complete: {analyzed} jobs analyzed")


async def scrape_linkedin_jobs(keywords, location, pages=1):
    """Scrape LinkedIn jobs using Playwright with human-like behavior"""
    jobs = []

    async with async_playwright() as p:
        # Launch browser with stealth settings
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ]
        )

        # Use random user agent and viewport
        ua = random_user_agent()
        vp = random_viewport()

        context = await browser.new_context(
            user_agent=ua,
            viewport=vp,
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Inject stealth scripts to hide automation
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        for page_num in range(pages):
            start = page_num * 25
            url = (
                f"https://www.linkedin.com/jobs/search/?"
                f"keywords={quote_plus(keywords)}&"
                f"location={quote_plus(location)}&"
                f"start={start}"
            )

            print(f"  🔍 Page {page_num + 1}: {url}")

            try:
                # Navigate with human-like delay first
                await human_delay(1, 3)
                await page.goto(url, wait_until="networkidle", timeout=45000)

                # Human-like scroll after page load
                await human_scroll(page)

                await page.wait_for_selector(".job-search-card", timeout=15000)

                job_cards = await page.query_selector_all(".job-search-card")

                for card in job_cards:
                    try:
                        # Basic fields
                        title_elem = await card.query_selector(".base-search-card__title")
                        company_elem = await card.query_selector(".base-search-card__subtitle")
                        location_elem = await card.query_selector(".job-search-card__location")
                        link_elem = await card.query_selector("a.base-card__full-link")

                        if not all([title_elem, company_elem, location_elem, link_elem]):
                            continue

                        title = (await title_elem.inner_text()).strip()
                        company = (await company_elem.inner_text()).strip()
                        job_location = (await location_elem.inner_text()).strip()
                        job_url = await link_elem.get_attribute("href")
                        job_url = job_url.split("?")[0] if job_url else None

                        # Enhanced fields - try to extract from metadata
                        # LinkedIn changed selectors - use base-search-card__metadata
                        metadata_elem = await card.query_selector(".base-search-card__metadata")
                        metadata_text = await metadata_elem.inner_text() if metadata_elem else ""

                        # Try to get posted date - check both the listdate element AND metadata
                        posted_elem = await card.query_selector(".job-search-card__listdate")
                        posted_text = await posted_elem.inner_text() if posted_elem else ""

                        # If not in listdate, try to extract from metadata text
                        if not posted_text and metadata_text:
                            # Look for patterns like "2 days ago", "1 week ago" in metadata
                            import re
                            match = re.search(r'(\d+\s*(?:day|week|hour|minute|month)s?\s*ago)', metadata_text, re.IGNORECASE)
                            if match:
                                posted_text = match.group(1)

                        posted_date = extract_posted_date(posted_text)

                        # Try to get work type from location (remote/hybrid keywords)
                        work_type = extract_work_type(job_location)

                        # Salary not available on job cards anymore - requires clicking into job
                        salary_min = None
                        salary_max = None
                        salary_currency = None

                        # Job type - extract from metadata if present
                        job_type = extract_job_type(metadata_text)

                        # Experience level - extract from metadata if present
                        experience_level = extract_experience_level(metadata_text)

                        # Applicants - not available on card
                        applicants_count = None

                        # Easy apply - not available on card
                        easy_apply = False

                        job_hash = generate_job_hash(title, company, job_location)

                        jobs.append({
                            "title": title,
                            "company": company,
                            "location": job_location,
                            "url": job_url,
                            "job_hash": job_hash,
                            "source": "linkedin",
                            # New enhanced fields
                            "salary_min": salary_min,
                            "salary_max": salary_max,
                            "salary_currency": salary_currency,
                            "job_type": job_type,
                            "experience_level": experience_level,
                            "work_type": work_type,
                            "posted_date": posted_date,
                            "applicants_count": applicants_count,
                            "easy_apply": easy_apply,
                        })
                    except Exception as e:
                        print(f"    ⚠️  Error parsing job card: {e}")
                        continue

                # Human-like delay between pages
                await human_delay(2, 5)

            except Exception as e:
                print(f"    ❌ Error on page {page_num + 1}: {e}")
                continue

        await browser.close()

    return jobs


async def scrape_for_user(user_id, config):
    """Scrape jobs for a single user configuration"""
    print(f"\n👤 User: {user_id}")
    print(f"   Keywords: {config['keywords']}")
    print(f"   Location: {config['location']}")
    print(f"   Pages: {config['pages']}")
    
    # Scrape jobs
    jobs = await scrape_linkedin_jobs(
        config["keywords"],
        config["location"],
        config["pages"]
    )
    
    if not jobs:
        print(f"  ⚠️  No jobs found")
        return 0
    
    print(f"  📦 Found {len(jobs)} jobs")
    
    # Save to database using Supabase client
    new_jobs = 0
    
    try:
        for job in jobs:
            # Check if job already exists
            existing = supabase.table("jobs")\
                .select("id")\
                .eq("job_hash", job["job_hash"])\
                .eq("user_id", user_id)\
                .execute()
            
            if existing.data:
                continue  # Skip duplicate
            
            # Insert new job
            supabase.table("jobs").insert({
                "user_id": user_id,
                "title": job["title"],
                "company": job["company"],
                "location": job["location"],
                "url": job["url"],
                "job_hash": job["job_hash"],
                "source": job["source"],
                "status": "New",
                # New enhanced fields
                "salary_min": job.get("salary_min"),
                "salary_max": job.get("salary_max"),
                "salary_currency": job.get("salary_currency"),
                "job_type": job.get("job_type"),
                "experience_level": job.get("experience_level"),
                "work_type": job.get("work_type"),
                "posted_date": job.get("posted_date"),
                "applicants_count": job.get("applicants_count"),
                "easy_apply": job.get("easy_apply"),
            }).execute()

            new_jobs += 1

        print(f"  ✅ Saved {new_jobs} new jobs")

        # Run AI analysis on new jobs
        if new_jobs > 0:
            # Get the newly inserted jobs with their IDs
            new_job_list = []
            for job in jobs:
                existing = supabase.table("jobs")\
                    .select("id, title, url")\
                    .eq("job_hash", job["job_hash"])\
                    .eq("user_id", user_id)\
                    .execute()
                if existing.data:
                    new_job_list.append(existing.data[0])

            # Run AI analysis
            if new_job_list:
                await analyze_new_jobs(user_id, new_job_list)

    except Exception as e:
        print(f"  ❌ Database error: {e}")
    
    return new_jobs


async def main():
    """Main scraper - runs for all active user configurations"""
    print("=" * 60)
    print("🌪️  ZEPHYR SCRAPER V2")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Get active search configs
        response = supabase.table("search_configs")\
            .select("id, user_id, keywords, location, pages")\
            .eq("is_active", True)\
            .execute()
        
        configs = response.data
        
        if not configs:
            print("\n⚠️  No active search configurations found")
            return
        
        print(f"\n📋 Found {len(configs)} active search configuration(s)")
        print("-" * 60)
        
        total_new_jobs = 0
        
        for config in configs:
            try:
                new_jobs = await scrape_for_user(config["user_id"], config)
                total_new_jobs += new_jobs
                await asyncio.sleep(SCRAPE_DELAY)
            except Exception as e:
                print(f"  ❌ Error: {str(e)}")
                continue
        
        print("\n" + "=" * 60)
        print(f"✅ SCRAPING COMPLETE")
        print(f"📊 Total new jobs saved: {total_new_jobs}")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())

