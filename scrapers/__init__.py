"""
Job-board scrapers.

LinkedIn lives in the top-level scraper.py (Playwright-based, unchanged).
This package holds the API-based boards: Greenhouse and Lever, both free
public JSON APIs with no auth and no anti-bot.

Each module exposes:
    async def scrape(keywords, location, pages) -> list[dict]

returning job dicts shaped like the LinkedIn scraper's output, plus a
`description` key (these APIs return the full description inline, so the
analysis step does not need to re-fetch it).
"""
