"""
Zephyr Multi-User Job Scraper - Supabase Version
Scrapes LinkedIn jobs for ALL users and saves to Supabase
"""

import os
import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
from supabase import create_client, Client
from typing import List, Dict

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")  # Service role for backend

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing Supabase credentials in environment variables")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def scrape_linkedin_jobs(keywords: str, location: str, pages: int = 2) -> List[Dict]:
    """
    Scrape LinkedIn jobs using public API endpoint
    """
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    headers = {
        "accept": "*/*",
        "accept-language": "en-US,en;q=0.9",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
    }

    params = {
        "keywords": keywords,
        "location": location,
        "trk": "public_jobs_jobs-search-bar_search-submit",
        "start": "0"
    }

    job_postings = []

    async with httpx.AsyncClient(timeout=30.0) as client:
        for page in range(pages):
            try:
                params["start"] = str(page * 25)

                print(f"  📄 Page {page + 1}/{pages}...", end=" ")

                response = await client.get(base_url, headers=headers, params=params)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "lxml")
                job_li_elements = soup.select("li")

                page_jobs = 0
                for job_li in job_li_elements:
                    link_element = job_li.select_one('a[data-tracking-control-name="public_jobs_jserp-result_search-card"]')
                    if not link_element:
                        continue

                    job_url = link_element.get("href", "")
                    job_id = job_url.split("/")[-1].split("?")[0] if job_url else ""

                    title_element = job_li.select_one("h3.base-search-card__title")
                    title = title_element.text.strip() if title_element else "N/A"

                    company_element = job_li.select_one("h4.base-search-card__subtitle")
                    company = company_element.text.strip() if company_element else "N/A"

                    location_element = job_li.select_one("span.job-search-card__location")
                    job_location = location_element.text.strip() if location_element else location

                    date_element = job_li.select_one("time.job-search-card__listdate")
                    posted_date = date_element.get("datetime", "") if date_element else ""

                    job_posting = {
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": job_location,
                        "posted_date": posted_date or None,
                        "url": job_url,
                        "keywords": keywords,
                    }

                    job_postings.append(job_posting)
                    page_jobs += 1

                print(f"{page_jobs} jobs found")

                # Rate limiting
                await asyncio.sleep(2)

            except Exception as e:
                print(f"❌ Error on page {page + 1}: {str(e)}")
                continue

    return job_postings

async def scrape_for_user(user_id: str, config: Dict) -> int:
    """Scrape jobs for a single user configuration"""
    keywords = config["keywords"]
    location = config["location"]
    pages = config.get("pages", 2)
    config_id = config["id"]

    print(f"\n🔍 Scraping: '{keywords}' in '{location}' (User: {user_id[:8]}...)")

    jobs = await scrape_linkedin_jobs(keywords, location, pages)

    if not jobs:
        print("  ⚠️  No jobs found")
        return 0

    # Add user_id and config_id to each job
    for job in jobs:
        job["user_id"] = user_id
        job["search_config_id"] = config_id
        job["status"] = "New"
        job["notes"] = ""

    # Insert jobs (unique constraint handles deduplication)
    inserted = 0
    for job in jobs:
        try:
            supabase.table("jobs").insert(job).execute()
            inserted += 1
        except Exception as e:
            # Likely duplicate - skip silently
            if "duplicate" not in str(e).lower():
                print(f"  ⚠️  Error inserting job: {str(e)}")

    print(f"  ✅ Saved {inserted}/{len(jobs)} new jobs")
    return inserted

async def main():
    """Main scraper - runs for all active user configurations"""
    print("=" * 60)
    print("🌪️  ZEPHYR MULTI-USER SCRAPER")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Fetch all active search configurations
    try:
        response = supabase.table("search_configs")\
                          .select("*, profiles(username)")\
                          .eq("is_active", True)\
                          .execute()

        configs = response.data

        if not configs:
            print("\n⚠️  No active search configurations found")
            return

        print(f"\n📋 Found {len(configs)} active search configurations")
        print("-" * 60)

        total_new_jobs = 0

        # Process each configuration
        for config in configs:
            user_id = config["user_id"]
            username = config.get("profiles", {}).get("username", "Unknown")

            try:
                new_jobs = await scrape_for_user(user_id, config)
                total_new_jobs += new_jobs

                # Sleep between users to be nice to LinkedIn
                await asyncio.sleep(3)

            except Exception as e:
                print(f"  ❌ Error for user {username}: {str(e)}")
                continue

        print("\n" + "=" * 60)
        print(f"✅ SCRAPING COMPLETE")
        print(f"📊 Total new jobs saved: {total_new_jobs}")
        print(f"⏰ Finished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ Fatal error: {str(e)}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
