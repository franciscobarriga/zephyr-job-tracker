"""
Zephyr Job Scraper
Scrapes LinkedIn jobs via public API and saves to Google Sheets
"""

import os
import yaml
import asyncio
import httpx
from bs4 import BeautifulSoup
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from typing import List, Dict
import time
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Google Sheets setup
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

def load_config() -> Dict:
    """Load configuration from config.yaml"""
    with open('config.yaml', 'r') as f:
        return yaml.safe_load(f)

def get_google_sheets_client():
    """Initialize Google Sheets client using service account"""
    creds_dict = {
        "type": os.environ.get("GSHEETS_TYPE"),
        "project_id": os.environ.get("GSHEETS_PROJECT_ID"),
        "private_key_id": os.environ.get("GSHEETS_PRIVATE_KEY_ID"),
        "private_key": os.environ.get("GSHEETS_PRIVATE_KEY").replace('\\n', '\n'),
        "client_email": os.environ.get("GSHEETS_CLIENT_EMAIL"),
        "client_id": os.environ.get("GSHEETS_CLIENT_ID"),
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_x509_cert_url": os.environ.get("GSHEETS_CLIENT_CERT_URL")
    }

    credentials = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    return gspread.authorize(credentials)

async def scrape_linkedin_jobs(keywords: str, location: str, pages: int = 3) -> List[Dict]:
    """
    Scrape LinkedIn jobs using public API endpoint

    Args:
        keywords: Job search keywords (e.g., "data engineer")
        location: Job location (e.g., "Madrid" or "Remote")
        pages: Number of pages to scrape (default 3)

    Returns:
        List of job dictionaries
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

                print(f"Scraping page {page + 1}/{pages} for '{keywords}' in '{location}'...")

                response = await client.get(base_url, headers=headers, params=params)
                response.raise_for_status()

                soup = BeautifulSoup(response.content, "lxml")
                job_li_elements = soup.select("li")

                for job_li in job_li_elements:
                    # Extract job URL and ID
                    link_element = job_li.select_one('a[data-tracking-control-name="public_jobs_jserp-result_search-card"]')
                    if not link_element:
                        continue

                    job_url = link_element.get("href", "")
                    job_id = job_url.split("/")[-1].split("?")[0] if job_url else ""

                    # Extract title
                    title_element = job_li.select_one("h3.base-search-card__title")
                    title = title_element.text.strip() if title_element else "N/A"

                    # Extract company
                    company_element = job_li.select_one("h4.base-search-card__subtitle")
                    company = company_element.text.strip() if company_element else "N/A"

                    # Extract location
                    location_element = job_li.select_one("span.job-search-card__location")
                    job_location = location_element.text.strip() if location_element else location

                    # Extract posted date
                    date_element = job_li.select_one("time.job-search-card__listdate")
                    posted_date = date_element.get("datetime", "") if date_element else ""

                    job_posting = {
                        "job_id": job_id,
                        "title": title,
                        "company": company,
                        "location": job_location,
                        "posted_date": posted_date,
                        "url": job_url,
                        "keywords": keywords,
                        "scraped_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "status": "New",
                        "notes": ""
                    }

                    job_postings.append(job_posting)

                # Rate limiting
                await asyncio.sleep(2)

            except Exception as e:
                print(f"Error scraping page {page + 1}: {str(e)}")
                continue

    print(f"Scraped {len(job_postings)} jobs")
    return job_postings

def deduplicate_jobs(new_jobs: List[Dict], existing_job_ids: List[str]) -> List[Dict]:
    """Remove jobs that already exist in the sheet"""
    return [job for job in new_jobs if job["job_id"] not in existing_job_ids]

def save_to_google_sheets(jobs: List[Dict], sheet_url: str):
    """Save jobs to Google Sheets"""
    if not jobs:
        print("No new jobs to save")
        return

    try:
        client = get_google_sheets_client()
        sheet = client.open_by_url(sheet_url).sheet1

        # Get existing job IDs to avoid duplicates
        existing_data = sheet.get_all_values()
        existing_job_ids = [row[0] for row in existing_data[1:]] if len(existing_data) > 1 else []

        # Deduplicate
        unique_jobs = deduplicate_jobs(jobs, existing_job_ids)

        if not unique_jobs:
            print("All jobs already exist in the sheet")
            return

        # Append new jobs
        rows_to_add = [
            [
                job["job_id"],
                job["title"],
                job["company"],
                job["location"],
                job["posted_date"],
                job["url"],
                job["keywords"],
                job["scraped_date"],
                job["status"],
                job["notes"]
            ]
            for job in unique_jobs
        ]

        sheet.append_rows(rows_to_add)
        print(f"Added {len(unique_jobs)} new jobs to Google Sheets")

    except Exception as e:
        print(f"Error saving to Google Sheets: {str(e)}")
        raise

async def main():
    """Main execution function"""
    config = load_config()

    # Get sheet URL from environment or config
    sheet_url = os.environ.get("GOOGLE_SHEET_URL", config.get("google_sheet_url", ""))

    if not sheet_url:
        raise ValueError("GOOGLE_SHEET_URL not found in environment or config")

    all_jobs = []

    # Scrape for each keyword-location combination
    for search in config.get("searches", []):
        keywords = search.get("keywords", "")
        location = search.get("location", "")
        pages = search.get("pages", 2)

        if keywords and location:
            jobs = await scrape_linkedin_jobs(keywords, location, pages)
            all_jobs.extend(jobs)

            # Sleep between searches to avoid rate limiting
            await asyncio.sleep(3)

    # Save to Google Sheets
    if all_jobs:
        save_to_google_sheets(all_jobs, sheet_url)
    else:
        print("No jobs scraped")

if __name__ == "__main__":
    asyncio.run(main())
