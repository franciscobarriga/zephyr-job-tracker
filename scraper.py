"""
Zephyr Job Scraper V3 - Enhanced Version
Scrapes additional fields from LinkedIn for richer job data
"""

import os
import asyncio
import hashlib
import re
from datetime import datetime
from urllib.parse import quote_plus
from supabase import create_client, Client
from playwright.async_api import async_playwright

# Configuration
SCRAPE_DELAY = 3  # seconds between users

# Initialize Supabase client
supabase: Client = create_client(
    os.environ.get("SUPABASE_URL"),
    os.environ.get("SUPABASE_SERVICE_KEY")
)


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


async def scrape_linkedin_jobs(keywords, location, pages=1):
    """Scrape LinkedIn jobs using Playwright"""
    jobs = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
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
                await page.goto(url, wait_until="networkidle", timeout=30000)
                await page.wait_for_selector(".job-search-card", timeout=10000)

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
                        metadata_elem = await card.query_selector(".job-search-card__metadata")
                        metadata_text = await metadata_elem.inner_text() if metadata_elem else ""

                        salary_elem = await card.query_selector(".job-card-container__salary-info")
                        salary_text = await salary_elem.inner_text() if salary_elem else ""

                        # Extract all the new fields
                        salary_min, salary_max, salary_currency = extract_salary(salary_text)
                        job_type = extract_job_type(metadata_text)
                        experience_level = extract_experience_level(metadata_text)
                        work_type = extract_work_type(metadata_text)

                        # Try to get posted date from another element
                        posted_elem = await card.query_selector(".job-card-container__listed-time")
                        posted_text = await posted_elem.inner_text() if posted_elem else ""
                        posted_date = extract_posted_date(posted_text)

                        # Try to get applicants count
                        applicants_elem = await card.query_selector(".job-card-container__ApplicantCount")
                        applicants_text = await applicants_elem.inner_text() if applicants_elem else ""
                        applicants_count = None
                        if applicants_text:
                            app_match = re.search(r'(\d+)', applicants_text.replace(",", ""))
                            if app_match:
                                applicants_count = int(app_match.group(1))

                        # Easy apply badge
                        easy_apply_elem = await card.query_selector(".job-card-container__apply-method")
                        easy_apply = easy_apply_elem is not None

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

                await asyncio.sleep(2)

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

