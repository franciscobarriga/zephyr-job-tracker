import pytest
import respx
import httpx


class TestLeverScrapeCompany:
    @pytest.mark.asyncio
    async def test_fetches_and_keyword_filters(self):
        payload = [
            {
                "text": "Senior Backend Engineer",
                "categories": {"location": "Remote"},
                "hostedUrl": "https://jobs.lever.co/acme/abc-123",
                "descriptionPlain": "Looking for a backend engineer.",
            },
            {
                "text": "Product Designer",
                "categories": {"location": "San Francisco"},
                "hostedUrl": "https://jobs.lever.co/acme/def-456",
                "descriptionPlain": "Design our product.",
            },
        ]
        with respx.mock:
            respx.get("https://api.lever.co/v0/postings/acme").mock(
                return_value=httpx.Response(200, json=payload)
            )
            from scrapers.lever import scrape_company
            jobs = await scrape_company("acme", "Backend")

        assert len(jobs) == 1
        j = jobs[0]
        assert j["title"] == "Senior Backend Engineer"
        assert j["company"] == "Acme"
        assert j["source"] == "lever"
        assert j["work_type"] == "Remote"
        assert j["description"] == "Looking for a backend engineer."

    @pytest.mark.asyncio
    async def test_returns_empty_on_error(self):
        with respx.mock:
            respx.get("https://api.lever.co/v0/postings/badco").mock(
                return_value=httpx.Response(500)
            )
            from scrapers.lever import scrape_company
            assert await scrape_company("badco", "Engineer") == []

    @pytest.mark.asyncio
    async def test_skips_jobs_without_url(self):
        payload = [
            {"text": "Engineer", "categories": {"location": "NY"},
             "hostedUrl": "", "descriptionPlain": "x"},
        ]
        with respx.mock:
            respx.get("https://api.lever.co/v0/postings/acme").mock(
                return_value=httpx.Response(200, json=payload)
            )
            from scrapers.lever import scrape_company
            assert await scrape_company("acme", "Engineer") == []
