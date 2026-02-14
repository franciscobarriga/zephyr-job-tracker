"""
Zephyr Job Scraper V2 - Direct PostgreSQL Version
Bypasses Supabase client to avoid PostgREST caching issues
"""

import os
import asyncio
import hashlib
from datetime import datetime
from urllib.parse import quote_plus
import psycopg2
from psycopg2.extras import RealDictCursor
from playwright.async_api import async_playwright

# Configuration
SCRAPE_DELAY = 3  # seconds between users


def get_db_connection():
    """Create direct PostgreSQL connection"""
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    return psycopg2.connect(database_url, cursor_factory=RealDictCursor)


def generate_job_hash(title, company, location):
    """Generate unique hash for job deduplication"""
    unique_string = f"{title}_{company}_{location}".lower()
    return hashlib.sha256(unique_string.encode()).hexdigest()


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
                        title_elem = await card.query_selector(".base-search-card__title")
                        company_elem = await card.query_selector(".base-search-card__subtitle")
                        location_elem = await card.query_selector(".job-search-card__location")
                        link_elem = await card.query_selector("a.base-card__full-link")
                        
                        if all([title_elem, company_elem, location_elem, link_elem]):
                            title = (await title_elem.inner_text()).strip()
                            company = (await company_elem.inner_text()).strip()
                            job_location = (await location_elem.inner_text()).strip()
                            job_url = await link_elem.get_attribute("href")
                            job_url = job_url.split("?")[0] if job_url else None
                            
                            job_hash = generate_job_hash(title, company, job_location)
                            
                            jobs.append({
                                "title": title,
                                "company": company,
                                "location": job_location,
                                "url": job_url,
                                "job_hash": job_hash,
                                "source": "linkedin",
                            })
                    except Exception as e:
                        print(f"    ⚠️  Error parsing job card: {e}")
                        continue
                
                await asyncio.sleep(2)  # Rate limiting
                
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
    
    # Save to database
    conn = get_db_connection()
    cursor = conn.cursor()
    
    new_jobs = 0
    
    try:
        for job in jobs:
            # Check if job already exists
            cursor.execute(
                "SELECT id FROM jobs WHERE job_hash = %s AND user_id = %s",
                (job["job_hash"], user_id)
            )
            
            if cursor.fetchone():
                continue  # Skip duplicate
            
            # Insert new job
            cursor.execute(
                """
                INSERT INTO jobs (
                    user_id, title, company, location, url, 
                    job_hash, source, created_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                """,
                (
                    user_id,
                    job["title"],
                    job["company"],
                    job["location"],
                    job["url"],
                    job["job_hash"],
                    job["source"]
                )
            )
            new_jobs += 1
        
        conn.commit()
        print(f"  ✅ Saved {new_jobs} new jobs")
        
    except Exception as e:
        conn.rollback()
        print(f"  ❌ Database error: {e}")
    finally:
        cursor.close()
        conn.close()
    
    return new_jobs


async def main():
    """Main scraper - runs for all active user configurations"""
    print("=" * 60)
    print("🌪️  ZEPHYR SCRAPER V2")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get active search configs
        cursor.execute("""
            SELECT id, user_id, keywords, location, pages 
            FROM search_configs 
            WHERE is_active = true
        """)
        configs = cursor.fetchall()
        
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
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    asyncio.run(main())

