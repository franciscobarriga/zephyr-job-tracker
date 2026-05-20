import pytest
import respx
import httpx


class TestGreenhouseScrapeCompany:
    @pytest.mark.asyncio
    async def test_fetches_and_keyword_filters(self):
        payload = {
            "jobs": [
                {
                    "title": "Backend Engineer",
                    "location": {"name": "San Francisco, CA"},
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/1",
                    "content": "<p>We build payments&nbsp;infrastructure.</p>",
                },
                {
                    "title": "Marketing Manager",
                    "location": {"name": "Remote"},
                    "absolute_url": "https://boards.greenhouse.io/acme/jobs/2",
                    "content": "<p>Own the funnel.</p>",
                },
            ]
        }
        with respx.mock:
            respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
                return_value=httpx.Response(200, json=payload)
            )
            from scrapers.greenhouse import scrape_company
            jobs = await scrape_company("acme", "Backend")

        assert len(jobs) == 1
        j = jobs[0]
        assert j["title"] == "Backend Engineer"
        assert j["company"] == "Acme"
        assert j["source"] == "greenhouse"
        assert "<p>" not in j["description"]
        assert "payments infrastructure" in j["description"]

    @pytest.mark.asyncio
    async def test_returns_empty_on_404(self):
        with respx.mock:
            respx.get("https://boards-api.greenhouse.io/v1/boards/nope/jobs").mock(
                return_value=httpx.Response(404)
            )
            from scrapers.greenhouse import scrape_company
            assert await scrape_company("nope", "Engineer") == []

    @pytest.mark.asyncio
    async def test_skips_jobs_without_url(self):
        payload = {"jobs": [
            {"title": "Engineer", "location": {"name": "NY"}, "absolute_url": "", "content": ""},
        ]}
        with respx.mock:
            respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
                return_value=httpx.Response(200, json=payload)
            )
            from scrapers.greenhouse import scrape_company
            assert await scrape_company("acme", "Engineer") == []

    @pytest.mark.asyncio
    async def test_remote_work_type_detected(self):
        payload = {"jobs": [
            {"title": "Data Analyst", "location": {"name": "Remote - US"},
             "absolute_url": "https://boards.greenhouse.io/acme/jobs/9", "content": "x"},
        ]}
        with respx.mock:
            respx.get("https://boards-api.greenhouse.io/v1/boards/acme/jobs").mock(
                return_value=httpx.Response(200, json=payload)
            )
            from scrapers.greenhouse import scrape_company
            jobs = await scrape_company("acme", "Data Analyst")
        assert jobs[0]["work_type"] == "Remote"
