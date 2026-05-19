# Resume & AI Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add resume upload/parsing, migrate AI from local Ollama to Claude API, and score every job against the user's resume.

**Architecture:** A new `app/utils/` layer holds the Claude API client and resume parser. The existing scraper and jobs route swap their Ollama `requests.post` call for the new client. A `match_score` column is added to jobs so the UI can filter/sort by fit.

**Tech Stack:** Claude API (`anthropic` SDK, claude-sonnet-4-6), `pdfplumber` (PDF parsing), `python-docx` (DOCX parsing), FastAPI `UploadFile`, Supabase Postgres, pytest + httpx + unittest.mock.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `app/utils/__init__.py` | Package marker |
| Create | `app/utils/ai_client.py` | Claude API wrapper — analyze_job, score_job_match |
| Create | `app/utils/resume_parser.py` | PDF/DOCX → plain text |
| Create | `app/routes/resume.py` | Upload + view profile routes |
| Create | `app/templates/resume.html` | Resume upload UI |
| Modify | `app/main.py` | Include resume router, add nav link |
| Modify | `scraper.py` | Swap Ollama calls → ai_client; run match scoring |
| Modify | `app/routes/jobs.py` | Swap Ollama call → ai_client; fix asyncio.run bug |
| Modify | `requirements.txt` | Add anthropic, pdfplumber, python-docx |
| Create | `tests/__init__.py` | Package marker |
| Create | `tests/conftest.py` | Shared fixtures (mock supabase, mock anthropic) |
| Create | `tests/test_ai_client.py` | Unit tests for analyze_job, score_job_match |
| Create | `tests/test_resume_parser.py` | Unit tests for parse_resume |
| Create | `tests/test_resume_routes.py` | Integration tests for upload endpoint |

---

## Task 1: DB Migration + Dependencies

**Files:**
- Modify: `requirements.txt`
- SQL to run in Supabase dashboard (no migration file needed)

- [ ] **Step 1: Add new dependencies**

Replace `requirements.txt` with:

```
# FastAPI Requirements
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
python-multipart>=0.0.6
jinja2>=3.1.3
itsdangerous>=2.1.2

# Database
supabase>=2.3.0

# AI
anthropic>=0.40.0

# Scraping
playwright>=1.48.0
httpx>=0.26.0
beautifulsoup4>=4.12.0

# Resume parsing
pdfplumber>=0.11.0
python-docx>=1.1.0

# Utilities
pandas>=2.0.0
python-dateutil>=2.8.0
python-dotenv>=1.0.0

# Testing
pytest>=8.0.0
pytest-asyncio>=0.23.0
httpx>=0.26.0
```

- [ ] **Step 2: Install dependencies**

```bash
cd /Users/panchis/Documents/Zephyr
source venv/bin/activate
pip install -r requirements.txt
```

Expected: All packages install without error.

- [ ] **Step 3: Run DB migration in Supabase**

In the Supabase dashboard SQL editor, run:

```sql
-- Add resume storage to profiles
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS resume_text TEXT,
  ADD COLUMN IF NOT EXISTS resume_filename TEXT;

-- Add match scoring to jobs
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS match_score INTEGER,
  ADD COLUMN IF NOT EXISTS match_reasoning TEXT;
```

Expected: No errors. Verify in Table Editor that columns appear.

- [ ] **Step 4: Add ANTHROPIC_API_KEY to .env**

Open `.env` and add:

```
ANTHROPIC_API_KEY=sk-ant-...your-key-here...
```

- [ ] **Step 5: Commit**

```bash
git add requirements.txt .env.example
git commit -m "feat: add anthropic/pdfplumber deps + DB columns for resume + match score"
```

---

## Task 2: Claude API Client

**Files:**
- Create: `app/utils/__init__.py`
- Create: `app/utils/ai_client.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_ai_client.py`

- [ ] **Step 1: Create package markers**

```bash
touch app/utils/__init__.py tests/__init__.py
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_ai_client.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch


def _make_message_response(text: str):
    """Build a minimal mock anthropic Message response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]
    return mock_response


class TestAnalyzeJob:
    def test_returns_summary_and_requirements(self):
        payload = json.dumps({
            "summary": "A fintech startup building payment APIs. Role focuses on Python backend.",
            "requirements": ["Python", "FastAPI", "PostgreSQL"]
        })
        with patch("app.utils.ai_client._client") as mock_client:
            mock_client.messages.create.return_value = _make_message_response(payload)
            from app.utils.ai_client import analyze_job
            result = analyze_job("some job description")

        assert result["summary"] == "A fintech startup building payment APIs. Role focuses on Python backend."
        assert result["requirements"] == "Python, FastAPI, PostgreSQL"

    def test_handles_empty_description(self):
        from app.utils.ai_client import analyze_job
        result = analyze_job("")
        assert result == {"summary": "—", "requirements": ""}

    def test_strips_markdown_code_block(self):
        payload = "```json\n" + json.dumps({"summary": "A role.", "requirements": ["Go"]}) + "\n```"
        with patch("app.utils.ai_client._client") as mock_client:
            mock_client.messages.create.return_value = _make_message_response(payload)
            from app.utils.ai_client import analyze_job
            result = analyze_job("some job description")

        assert result["requirements"] == "Go"

    def test_returns_empty_requirements_when_none(self):
        payload = json.dumps({"summary": "A role.", "requirements": []})
        with patch("app.utils.ai_client._client") as mock_client:
            mock_client.messages.create.return_value = _make_message_response(payload)
            from app.utils.ai_client import analyze_job
            result = analyze_job("some job")

        assert result["requirements"] == ""


class TestScoreJobMatch:
    def test_returns_score_and_reasoning(self):
        payload = json.dumps({"score": 82, "reasoning": "Strong Python and FastAPI match."})
        with patch("app.utils.ai_client._client") as mock_client:
            mock_client.messages.create.return_value = _make_message_response(payload)
            from app.utils.ai_client import score_job_match
            result = score_job_match("job desc", "resume text")

        assert result["score"] == 82
        assert "Python" in result["reasoning"]

    def test_returns_zero_score_for_empty_inputs(self):
        from app.utils.ai_client import score_job_match
        result = score_job_match("", "")
        assert result["score"] == 0
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
pytest tests/test_ai_client.py -v
```

Expected: `ImportError` or `ModuleNotFoundError` — `app.utils.ai_client` doesn't exist yet.

- [ ] **Step 4: Implement `app/utils/ai_client.py`**

```python
import json
import re
import anthropic

_client = anthropic.Anthropic()

_SYSTEM = "You are an expert technical recruiter. Analyze job postings and extract structured information. Return only valid JSON."

_SYSTEM_BLOCK = [{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}]


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw.strip())


def analyze_job(description: str) -> dict:
    if not description:
        return {"summary": "—", "requirements": ""}

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=512,
        system=_SYSTEM_BLOCK,
        messages=[{
            "role": "user",
            "content": (
                "Analyze this job posting and return ONLY valid JSON:\n"
                '{"summary": "2-3 sentences: what the company does, the role, YOE if stated",'
                ' "requirements": ["tool1", "skill2"]}\n\n'
                "Rules:\n"
                "- requirements: hard skills and tools only, no soft skills\n"
                "- requirements: [] if none found\n\n"
                f"Job posting:\n{description[:3000]}"
            )
        }]
    )

    parsed = _parse_json(response.content[0].text)
    reqs = [r for r in parsed.get("requirements", []) if r]
    return {
        "summary": parsed.get("summary", "—"),
        "requirements": ", ".join(reqs),
    }


def score_job_match(job_description: str, resume_text: str) -> dict:
    if not job_description or not resume_text:
        return {"score": 0, "reasoning": "Insufficient data"}

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        system=_SYSTEM_BLOCK,
        messages=[{
            "role": "user",
            "content": (
                "Score how well this candidate matches this job. Return ONLY valid JSON:\n"
                '{"score": <0-100>, "reasoning": "<one sentence>"}\n\n'
                f"Resume:\n{resume_text[:2000]}\n\n"
                f"Job posting:\n{job_description[:2000]}"
            )
        }]
    )

    parsed = _parse_json(response.content[0].text)
    return {
        "score": int(parsed.get("score", 0)),
        "reasoning": parsed.get("reasoning", ""),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_ai_client.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/utils/__init__.py app/utils/ai_client.py tests/__init__.py tests/test_ai_client.py
git commit -m "feat: add Claude API client with analyze_job and score_job_match"
```

---

## Task 3: Resume Parser

**Files:**
- Create: `app/utils/resume_parser.py`
- Create: `tests/test_resume_parser.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_resume_parser.py`:

```python
import io
import pytest
from unittest.mock import MagicMock, patch


class TestParseResume:
    def test_raises_for_unsupported_extension(self):
        from app.utils.resume_parser import parse_resume
        with pytest.raises(ValueError, match="Unsupported file type"):
            parse_resume(b"data", "resume.txt")

    def test_parses_pdf(self):
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "John Doe\nSoftware Engineer"
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = lambda s: mock_pdf
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page]

        with patch("app.utils.resume_parser.pdfplumber.open", return_value=mock_pdf):
            from app.utils.resume_parser import parse_resume
            result = parse_resume(b"%PDF-fake", "resume.pdf")

        assert "John Doe" in result
        assert "Software Engineer" in result

    def test_parses_docx(self):
        mock_para1 = MagicMock()
        mock_para1.text = "Jane Smith"
        mock_para2 = MagicMock()
        mock_para2.text = "Data Engineer"
        mock_para3 = MagicMock()
        mock_para3.text = ""  # empty paragraphs should be skipped

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2, mock_para3]

        with patch("app.utils.resume_parser.Document", return_value=mock_doc):
            from app.utils.resume_parser import parse_resume
            result = parse_resume(b"PK-fake", "resume.docx")

        assert "Jane Smith" in result
        assert "Data Engineer" in result
        assert result.count("\n") == 1  # empty paragraph not included

    def test_pdf_skips_none_pages(self):
        mock_page1 = MagicMock()
        mock_page1.extract_text.return_value = "Page 1 content"
        mock_page2 = MagicMock()
        mock_page2.extract_text.return_value = None
        mock_pdf = MagicMock()
        mock_pdf.__enter__ = lambda s: mock_pdf
        mock_pdf.__exit__ = MagicMock(return_value=False)
        mock_pdf.pages = [mock_page1, mock_page2]

        with patch("app.utils.resume_parser.pdfplumber.open", return_value=mock_pdf):
            from app.utils.resume_parser import parse_resume
            result = parse_resume(b"%PDF-fake", "resume.pdf")

        assert result == "Page 1 content"
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_resume_parser.py -v
```

Expected: `ImportError` — module doesn't exist yet.

- [ ] **Step 3: Implement `app/utils/resume_parser.py`**

```python
import io
import pdfplumber
from docx import Document


def parse_resume(file_bytes: bytes, filename: str) -> str:
    name = filename.lower()
    if name.endswith(".pdf"):
        return _parse_pdf(file_bytes)
    if name.endswith((".docx", ".doc")):
        return _parse_docx(file_bytes)
    raise ValueError(f"Unsupported file type: {filename}")


def _parse_pdf(file_bytes: bytes) -> str:
    parts = []
    with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
    return "\n".join(parts)


def _parse_docx(file_bytes: bytes) -> str:
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_resume_parser.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/utils/resume_parser.py tests/test_resume_parser.py
git commit -m "feat: add PDF/DOCX resume parser"
```

---

## Task 4: Resume Upload Route + Template

**Files:**
- Create: `app/routes/resume.py`
- Create: `app/templates/resume.html`
- Create: `tests/test_resume_routes.py`

- [ ] **Step 1: Create `tests/conftest.py`**

```python
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_supabase():
    with patch("app.auth.supabase") as mock:
        yield mock


@pytest.fixture
def mock_current_user():
    return {"id": "test-user-uuid", "email": "test@example.com", "user_metadata": {"username": "testuser"}}
```

- [ ] **Step 2: Write failing tests**

Create `tests/test_resume_routes.py`:

```python
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import io


def _make_app_with_mocked_user(mock_user):
    """Create test app that injects a fake current user."""
    from app.main import app
    from app import auth

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[auth.get_current_user] = override_get_current_user
    return TestClient(app)


class TestResumeGet:
    def test_redirects_unauthenticated_user(self):
        from app.main import app
        client = TestClient(app, follow_redirects=False)
        resp = client.get("/resume/")
        assert resp.status_code in (302, 307)

    def test_shows_upload_form_when_no_resume(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        mock_profile_resp = MagicMock()
        mock_profile_resp.data = {"resume_text": None, "resume_filename": None}

        with patch("app.routes.resume.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile_resp
            client = _make_app_with_mocked_user(mock_user)
            resp = client.get("/resume/")

        assert resp.status_code == 200
        assert "Upload" in resp.text


class TestResumeUpload:
    def test_upload_pdf_updates_profile(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        fake_pdf_bytes = b"%PDF-1.4 fake content"

        with patch("app.routes.resume.parse_resume", return_value="John Doe\nEngineer") as mock_parse, \
             patch("app.routes.resume.supabase") as mock_sb:

            mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
            client = _make_app_with_mocked_user(mock_user)
            resp = client.post(
                "/resume/upload",
                files={"file": ("resume.pdf", io.BytesIO(fake_pdf_bytes), "application/pdf")},
                follow_redirects=False,
            )

        mock_parse.assert_called_once_with(fake_pdf_bytes, "resume.pdf")
        assert resp.status_code in (302, 303)

    def test_rejects_oversized_file(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        big_bytes = b"x" * (6 * 1024 * 1024)  # 6MB

        with patch("app.routes.resume.supabase"):
            client = _make_app_with_mocked_user(mock_user)
            resp = client.post(
                "/resume/upload",
                files={"file": ("big.pdf", io.BytesIO(big_bytes), "application/pdf")},
            )

        assert resp.status_code == 400
```

- [ ] **Step 3: Run tests to verify failure**

```bash
pytest tests/test_resume_routes.py -v
```

Expected: `ImportError` — `app.routes.resume` doesn't exist yet.

- [ ] **Step 4: Implement `app/routes/resume.py`**

```python
from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import get_current_user, supabase
from app.utils.resume_parser import parse_resume

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/", response_class=HTMLResponse)
async def resume_page(request: Request, user=Depends(get_current_user)):
    profile = (
        supabase.table("profiles")
        .select("resume_text, resume_filename")
        .eq("id", user["id"])
        .single()
        .execute()
    )
    data = profile.data or {}
    return templates.TemplateResponse("resume.html", {
        "request": request,
        "user": user,
        "has_resume": bool(data.get("resume_text")),
        "resume_filename": data.get("resume_filename"),
        "uploaded": request.query_params.get("uploaded") == "1",
    })


@router.post("/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    contents = await file.read()
    if len(contents) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    resume_text = parse_resume(contents, file.filename)

    supabase.table("profiles").update({
        "resume_text": resume_text,
        "resume_filename": file.filename,
    }).eq("id", user["id"]).execute()

    return RedirectResponse(url="/resume/?uploaded=1", status_code=303)
```

- [ ] **Step 5: Create `app/templates/resume.html`**

```html
{% extends "base.html" %}

{% block title %}Resume - Zephyr{% endblock %}

{% block content %}
<div class="page-header">
    <div class="page-title">
        <h1 class="mb-0"><i class="bi bi-file-earmark-person"></i> My Resume</h1>
    </div>
    <a href="/dashboard" class="btn btn-zephyr-secondary">
        <i class="bi bi-arrow-left me-2"></i>Back
    </a>
</div>

{% if uploaded %}
<div class="alert alert-success alert-dismissible fade show" role="alert">
    <i class="bi bi-check-circle me-2"></i>Resume uploaded successfully!
    <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
</div>
{% endif %}

<div class="card mb-4">
    <div class="card-header">
        <h5 class="mb-0"><i class="bi bi-upload me-2"></i>Upload Resume</h5>
    </div>
    <div class="card-body">
        {% if has_resume %}
        <div class="alert alert-info mb-3">
            <i class="bi bi-file-earmark-check me-2"></i>
            Current resume: <strong>{{ resume_filename }}</strong>
            — Upload a new file to replace it.
        </div>
        {% endif %}
        <form method="POST" action="/resume/upload" enctype="multipart/form-data">
            <div class="mb-3">
                <label for="file" class="form-label">Resume file (PDF or DOCX, max 5 MB)</label>
                <input type="file" class="form-control" id="file" name="file" accept=".pdf,.docx,.doc" required>
            </div>
            <button type="submit" class="btn btn-zephyr">
                <i class="bi bi-cloud-upload me-2"></i>Upload Resume
            </button>
        </form>
    </div>
</div>

{% if not has_resume %}
<div class="card">
    <div class="card-body text-center py-5">
        <i class="bi bi-file-earmark-person" style="font-size:3rem;color:var(--zephyr-primary);"></i>
        <h5 class="mt-3">No resume uploaded yet</h5>
        <p class="text-muted">Upload your resume to enable AI match scoring on job listings.</p>
    </div>
</div>
{% endif %}
{% endblock %}
```

- [ ] **Step 6: Run tests to verify they pass**

```bash
pytest tests/test_resume_routes.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 7: Commit**

```bash
git add app/routes/resume.py app/templates/resume.html tests/test_resume_routes.py tests/conftest.py
git commit -m "feat: resume upload route and template with 5MB size guard"
```

---

## Task 5: Wire Resume Router into App

**Files:**
- Modify: `app/main.py`
- Modify: `app/templates/base.html`

- [ ] **Step 1: Add resume router to `app/main.py`**

In `app/main.py`, add the import and include_router call:

```python
# At top with other route imports:
from app.routes import auth, dashboard, jobs, search, resume

# After the existing include_router calls:
app.include_router(resume.router, prefix="/resume", tags=["Resume"])
```

- [ ] **Step 2: Add Resume link to nav in `app/templates/base.html`**

Find the nav section in `base.html` and add alongside existing nav items:

```html
<a href="/resume" class="nav-link {% if request.url.path.startswith('/resume') %}active{% endif %}">
    <i class="bi bi-file-earmark-person"></i>
    <span>Resume</span>
</a>
```

- [ ] **Step 3: Smoke test manually**

```bash
cd /Users/panchis/Documents/Zephyr
source venv/bin/activate
python run.py
```

Open `http://localhost:8000/resume/` — should show the upload form. Upload a PDF and verify the success banner appears.

- [ ] **Step 4: Commit**

```bash
git add app/main.py app/templates/base.html
git commit -m "feat: wire resume router and nav link"
```

---

## Task 6: Migrate Scraper from Ollama to Claude API + Add Match Scoring

**Files:**
- Modify: `scraper.py`

The existing `analyze_job()` function at line 246 in `scraper.py` makes `requests.post` calls to `http://localhost:11434`. This breaks in GitHub Actions (no local Ollama). Replace it with the new `ai_client` module.

Also, `analyze_new_jobs()` runs after insertion — extend it to also call `score_job_match` if the user has a resume.

- [ ] **Step 1: Replace the import block at top of `scraper.py`**

Remove the `import requests` and `import json` lines (they're only used by the old Ollama code). Add:

```python
from app.utils.ai_client import analyze_job, score_job_match
```

- [ ] **Step 2: Remove the old `analyze_job()` function (lines 246–310)**

Delete the entire `analyze_job()` function body from `scraper.py`. It is now in `app/utils/ai_client.py`.

- [ ] **Step 3: Update `analyze_new_jobs()` to also run match scoring**

Replace the `analyze_new_jobs` function with:

```python
async def analyze_new_jobs(user_id, jobs_data):
    """Visit each new job URL, run AI analysis, and score against user resume."""
    if not jobs_data:
        return

    # Fetch user's resume text for match scoring
    profile_resp = supabase.table("profiles").select("resume_text").eq("id", user_id).single().execute()
    resume_text = (profile_resp.data or {}).get("resume_text") or ""

    print(f"  🤖 Running AI analysis on {len(jobs_data)} new jobs...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        analyzed = 0
        for job in jobs_data:
            try:
                description = await get_job_description(page, job["url"])
                if not description:
                    print(f"    ⚠️  No description found for: {job['title'][:30]}")
                    continue

                print(f"    📝 Analyzing: {job['title'][:30]}...")
                analysis = analyze_job(description)

                update_data = {
                    "description": description,
                    "ai_summary": analysis.get("summary"),
                    "ai_requirements": analysis.get("requirements"),
                }

                if resume_text:
                    match = score_job_match(description, resume_text)
                    update_data["match_score"] = match["score"]
                    update_data["match_reasoning"] = match["reasoning"]

                supabase.table("jobs").update(update_data).eq("id", job["id"]).execute()
                analyzed += 1
                await human_delay(1, 3)

            except Exception as e:
                print(f"    ⚠️  Error analyzing job: {e}")
                continue

        await browser.close()

    print(f"  ✅ AI analysis complete: {analyzed} jobs analyzed")
```

- [ ] **Step 4: Verify scraper imports cleanly**

```bash
cd /Users/panchis/Documents/Zephyr
source venv/bin/activate
python -c "import scraper; print('OK')"
```

Expected: `OK` with no errors.

- [ ] **Step 5: Commit**

```bash
git add scraper.py
git commit -m "feat: migrate scraper from Ollama to Claude API; add match scoring per job"
```

---

## Task 7: Update jobs.py fetch-description Endpoint

**Files:**
- Modify: `app/routes/jobs.py`

The `fetch_job_description` endpoint at line 100 has two bugs:
1. Calls `asyncio.run()` inside an already-running async context (raises `RuntimeError` in FastAPI)
2. Calls the old local `analyze_job` from `scraper.py` instead of the new client

- [ ] **Step 1: Replace the fetch-description endpoint in `app/routes/jobs.py`**

Remove the existing `fetch_job_description` function (lines 100–150) and replace with:

```python
@router.post("/{job_id}/fetch-description")
async def fetch_job_description(
    job_id: int,
    user=Depends(get_current_user),
):
    """Fetch job description from LinkedIn and run AI analysis."""
    from app.utils.ai_client import analyze_job, score_job_match
    from playwright.async_api import async_playwright

    response = supabase.table("jobs").select("url, title").eq("id", job_id).eq("user_id", user["id"]).execute()
    if not response.data:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    job_url = response.data[0].get("url")
    if not job_url:
        return JSONResponse({"error": "No URL for this job"}, status_code=400)

    import sys
    sys.path.insert(0, str(BASE_DIR.parent))
    from scraper import get_job_description

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        description = await get_job_description(page, job_url)
        await browser.close()

    if not description:
        return JSONResponse({"error": "Could not fetch description"}, status_code=422)

    analysis = analyze_job(description)

    profile = supabase.table("profiles").select("resume_text").eq("id", user["id"]).single().execute()
    resume_text = (profile.data or {}).get("resume_text") or ""

    update_data = {
        "description": description,
        "ai_summary": analysis.get("summary"),
        "ai_requirements": analysis.get("requirements"),
    }
    if resume_text:
        match = score_job_match(description, resume_text)
        update_data["match_score"] = match["score"]
        update_data["match_reasoning"] = match["reasoning"]

    supabase.table("jobs").update(update_data).eq("id", job_id).execute()

    return {"success": True, "description": description[:200] + "..."}
```

- [ ] **Step 2: Remove now-unused imports from `app/routes/jobs.py`**

At the top of `jobs.py`, remove:
```python
import requests
import json
```
These were only used by the old inline Ollama call.

- [ ] **Step 3: Verify the app starts cleanly**

```bash
python run.py
```

Expected: Starts without import errors. Open `http://localhost:8000/job-board/` and verify jobs still load.

- [ ] **Step 4: Commit**

```bash
git add app/routes/jobs.py
git commit -m "fix: replace asyncio.run bug + migrate fetch-description to Claude API"
```

---

## Task 8: Show Match Score in Job Board UI

**Files:**
- Modify: `app/templates/jobs.html`

- [ ] **Step 1: Add match score badge to job cards in `jobs.html`**

After the `<div class="job-card-status">` block (which shows the Applied/New/Thinking badge), add:

```html
{% if job.match_score is not none %}
<div class="job-card-match ms-2">
    {% set score = job.match_score %}
    {% if score >= 80 %}
        <span class="badge" style="background:#10b981;">
    {% elif score >= 60 %}
        <span class="badge" style="background:#f59e0b;">
    {% else %}
        <span class="badge bg-secondary">
    {% endif %}
        <i class="bi bi-stars me-1"></i>{{ score }}%
        </span>
</div>
{% endif %}
```

- [ ] **Step 2: Add match reasoning to the expanded job detail section**

Inside the job detail collapse area (look for `job-card-details` div), add after ai_summary:

```html
{% if job.match_score is not none %}
<div class="mt-2">
    <strong><i class="bi bi-stars me-1"></i>Match Score:</strong>
    <span class="{% if job.match_score >= 80 %}text-success{% elif job.match_score >= 60 %}text-warning{% else %}text-muted{% endif %}">
        {{ job.match_score }}%
    </span>
    {% if job.match_reasoning %}
    <div class="text-muted small mt-1">{{ job.match_reasoning }}</div>
    {% endif %}
</div>
{% endif %}
```

- [ ] **Step 3: Smoke test**

Start the app and open `http://localhost:8000/job-board/`. Jobs with a `match_score` should show a colored badge. Jobs without a score (scraped before this feature) show nothing.

- [ ] **Step 4: Commit**

```bash
git add app/templates/jobs.html
git commit -m "feat: show match score badge and reasoning on job cards"
```

---

## Task 9: Re-score Existing Jobs (Backfill)

When the user uploads their resume for the first time, existing jobs have no `match_score`. Add a backfill endpoint to score all existing unscored jobs.

**Files:**
- Modify: `app/routes/resume.py`

- [ ] **Step 1: Add backfill endpoint to `app/routes/resume.py`**

```python
@router.post("/rescore-all")
async def rescore_all_jobs(
    request: Request,
    user=Depends(get_current_user),
):
    """Re-score all jobs that don't have a match_score yet."""
    from app.utils.ai_client import score_job_match

    profile = supabase.table("profiles").select("resume_text").eq("id", user["id"]).single().execute()
    resume_text = (profile.data or {}).get("resume_text") or ""
    if not resume_text:
        return JSONResponse({"error": "No resume uploaded"}, status_code=400)

    jobs_resp = (
        supabase.table("jobs")
        .select("id, description")
        .eq("user_id", user["id"])
        .is_("match_score", "null")
        .not_.is_("description", "null")
        .execute()
    )
    jobs = jobs_resp.data or []

    scored = 0
    for job in jobs:
        try:
            match = score_job_match(job["description"], resume_text)
            supabase.table("jobs").update({
                "match_score": match["score"],
                "match_reasoning": match["reasoning"],
            }).eq("id", job["id"]).execute()
            scored += 1
        except Exception:
            continue

    return {"scored": scored, "total": len(jobs)}
```

- [ ] **Step 2: Add "Score All Jobs" button to `resume.html`**

Below the upload form card, add (only shown when resume exists):

```html
{% if has_resume %}
<div class="card">
    <div class="card-body d-flex align-items-center justify-content-between">
        <div>
            <h6 class="mb-1">Score existing jobs</h6>
            <p class="text-muted small mb-0">Run match scoring on all jobs that were scraped before your resume was uploaded.</p>
        </div>
        <button class="btn btn-zephyr-secondary ms-3" id="rescoreBtn" onclick="rescoreAll()">
            <i class="bi bi-stars me-2"></i>Score All
        </button>
    </div>
</div>
<script>
async function rescoreAll() {
    const btn = document.getElementById('rescoreBtn');
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Scoring...';
    const resp = await fetch('/resume/rescore-all', {method: 'POST'});
    const data = await resp.json();
    btn.disabled = false;
    btn.innerHTML = '<i class="bi bi-check-circle me-2"></i>Done (' + (data.scored || 0) + ' scored)';
}
</script>
{% endif %}
```

- [ ] **Step 3: Commit**

```bash
git add app/routes/resume.py app/templates/resume.html
git commit -m "feat: backfill match scores for existing jobs after resume upload"
```

---

## Self-Review

**Spec coverage:**
- ✅ Resume upload (PDF/DOCX) → `resume_parser.py` + `routes/resume.py`
- ✅ Store structured profile in DB → `resume_text` + `resume_filename` on `profiles`
- ✅ Claude API replacing Ollama → `ai_client.py` used in scraper + jobs route
- ✅ AI match scoring → `score_job_match` in scraper + fetch-description + backfill
- ✅ Match score visible in UI → job board badges

**Gaps addressed:**
- Fixed `asyncio.run()` inside async context bug in jobs.py (Task 7)
- Backfill endpoint for jobs scraped before resume was uploaded (Task 9)

**Type/name consistency check:**
- `analyze_job(description: str) -> dict` — used consistently in scraper.py Task 6 and jobs.py Task 7 ✅
- `score_job_match(job_description, resume_text) -> dict` — same signature everywhere ✅
- `parse_resume(file_bytes, filename) -> str` — same signature in routes and tests ✅
