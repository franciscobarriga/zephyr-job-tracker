# Tailored Resume & Cover Letter PDF Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Prerequisite:** Plan `2026-05-18-resume-ai-foundation.md` must be complete. `profiles.resume_text` must exist and `app/utils/ai_client.py` must be in place.

**Goal:** For any job, let the user generate a Claude-tailored resume (bullets rewritten to match the JD) and a cover letter, then download both as a single PDF.

**Architecture:** A new `app/utils/resume_tailor.py` prompts Claude with the user's original resume text + job description and returns structured tailored content. A `app/utils/pdf_generator.py` renders that content to PDF via WeasyPrint. A new route `app/routes/tailor.py` orchestrates both and caches the result in Supabase (`jobs.tailored_resume`, `jobs.cover_letter`). The job board gets a "Tailor & Download" button.

**Tech Stack:** Claude API (claude-sonnet-4-6, prompt caching), WeasyPrint, Jinja2 (for PDF HTML template), pytest + unittest.mock.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `app/utils/resume_tailor.py` | Claude prompts → tailored bullets + cover letter text |
| Create | `app/utils/pdf_generator.py` | HTML template → PDF bytes via WeasyPrint |
| Create | `app/templates/pdf_resume.html` | Standalone HTML used as PDF source |
| Create | `app/routes/tailor.py` | Generate + cache tailored docs; serve PDF download |
| Modify | `app/main.py` | Include tailor router |
| Modify | `app/templates/jobs.html` | Add "Tailor & Download" button per job card |
| Modify | `requirements.txt` | Add weasyprint |
| Create | `tests/test_resume_tailor.py` | Unit tests for tailor functions |
| Create | `tests/test_pdf_generator.py` | Unit tests for PDF rendering |

---

## Task 1: Install WeasyPrint

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Add WeasyPrint to requirements.txt**

Add to the `# Resume parsing` section in `requirements.txt`:

```
weasyprint>=62.0
```

- [ ] **Step 2: Install**

```bash
cd /Users/panchis/Documents/Zephyr
source venv/bin/activate
pip install weasyprint
```

Expected: Installs without error. WeasyPrint requires system libraries (`pango`, `cairo`) — on macOS run `brew install pango cairo` if it fails.

- [ ] **Step 3: DB migration**

In Supabase SQL editor:

```sql
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS tailored_resume TEXT,
  ADD COLUMN IF NOT EXISTS cover_letter TEXT,
  ADD COLUMN IF NOT EXISTS tailored_at TIMESTAMPTZ;
```

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "feat: add weasyprint dep + tailored doc columns to jobs table"
```

---

## Task 2: Resume Tailor Utility

**Files:**
- Create: `app/utils/resume_tailor.py`
- Create: `tests/test_resume_tailor.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_resume_tailor.py`:

```python
import json
import pytest
from unittest.mock import MagicMock, patch


def _make_message_response(text: str):
    mock = MagicMock()
    mock.content = [MagicMock(text=text)]
    return mock


class TestTailorResume:
    def test_returns_tailored_bullets_and_cover_letter(self):
        payload = json.dumps({
            "tailored_bullets": [
                "Built Python microservices handling 10k req/s",
                "Led migration to PostgreSQL reducing latency by 40%"
            ],
            "cover_letter": "Dear Hiring Manager, I am excited to apply..."
        })
        with patch("app.utils.resume_tailor._client") as mock_client:
            mock_client.messages.create.return_value = _make_message_response(payload)
            from app.utils.resume_tailor import tailor_for_job
            result = tailor_for_job(
                resume_text="I am an engineer with Python experience.",
                job_description="Looking for a Python backend engineer.",
                job_title="Backend Engineer",
                company="Acme Corp",
            )

        assert len(result["tailored_bullets"]) == 2
        assert "Dear Hiring Manager" in result["cover_letter"]

    def test_raises_on_empty_resume(self):
        from app.utils.resume_tailor import tailor_for_job
        with pytest.raises(ValueError, match="resume_text"):
            tailor_for_job("", "job desc", "Engineer", "Acme")

    def test_raises_on_empty_job_description(self):
        from app.utils.resume_tailor import tailor_for_job
        with pytest.raises(ValueError, match="job_description"):
            tailor_for_job("resume text", "", "Engineer", "Acme")

    def test_strips_markdown_code_blocks(self):
        inner = json.dumps({
            "tailored_bullets": ["Built APIs"],
            "cover_letter": "Dear team..."
        })
        payload = f"```json\n{inner}\n```"
        with patch("app.utils.resume_tailor._client") as mock_client:
            mock_client.messages.create.return_value = _make_message_response(payload)
            from app.utils.resume_tailor import tailor_for_job
            result = tailor_for_job("resume", "job", "Engineer", "Corp")

        assert result["tailored_bullets"] == ["Built APIs"]
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_resume_tailor.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `app/utils/resume_tailor.py`**

```python
import json
import re
import anthropic

_client = anthropic.Anthropic()

_SYSTEM = (
    "You are an expert resume writer and career coach. "
    "Your task is to tailor resumes and write cover letters that closely match a job description. "
    "Be specific, quantify achievements where possible, and mirror the language in the job description."
)

_SYSTEM_BLOCK = [{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}]


def tailor_for_job(
    resume_text: str,
    job_description: str,
    job_title: str,
    company: str,
) -> dict:
    """
    Returns:
        {
            "tailored_bullets": ["bullet 1", "bullet 2", ...],
            "cover_letter": "Full cover letter text..."
        }
    """
    if not resume_text:
        raise ValueError("resume_text is required")
    if not job_description:
        raise ValueError("job_description is required")

    response = _client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=2048,
        system=_SYSTEM_BLOCK,
        messages=[{
            "role": "user",
            "content": (
                f"I'm applying for the role of **{job_title}** at **{company}**.\n\n"
                "Tailor my resume bullets to match this job description, then write a cover letter. "
                "Return ONLY valid JSON:\n"
                '{\n'
                '  "tailored_bullets": ["rewritten bullet 1", "rewritten bullet 2", ...],\n'
                '  "cover_letter": "Full cover letter (3 paragraphs, professional tone)"\n'
                '}\n\n'
                "Rules:\n"
                "- tailored_bullets: 4-6 bullets rewritten from my resume to match the JD language\n"
                "- Each bullet starts with a strong action verb\n"
                "- Quantify achievements where my resume mentions numbers\n"
                "- cover_letter: address to 'Hiring Manager', sign off with 'Sincerely,'\n\n"
                f"My resume:\n{resume_text[:3000]}\n\n"
                f"Job description:\n{job_description[:2000]}"
            )
        }]
    )

    raw = response.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)

    return json.loads(raw.strip())
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_resume_tailor.py -v
```

Expected: All 4 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/utils/resume_tailor.py tests/test_resume_tailor.py
git commit -m "feat: Claude-powered resume tailor and cover letter generator"
```

---

## Task 3: PDF Generator

**Files:**
- Create: `app/utils/pdf_generator.py`
- Create: `app/templates/pdf_resume.html`
- Create: `tests/test_pdf_generator.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_pdf_generator.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


class TestGeneratePdf:
    def test_returns_bytes(self):
        fake_pdf_bytes = b"%PDF-1.4 fake"

        mock_html = MagicMock()
        mock_html.write_pdf.return_value = fake_pdf_bytes

        with patch("app.utils.pdf_generator.HTML") as mock_HTML:
            mock_HTML.return_value = mock_html
            from app.utils.pdf_generator import generate_tailored_pdf
            result = generate_tailored_pdf(
                job_title="Software Engineer",
                company="Acme",
                candidate_name="John Doe",
                tailored_bullets=["Led team of 5", "Built APIs"],
                cover_letter="Dear Hiring Manager...",
            )

        assert isinstance(result, bytes)
        assert result == fake_pdf_bytes

    def test_passes_html_string_to_weasyprint(self):
        mock_html_instance = MagicMock()
        mock_html_instance.write_pdf.return_value = b"%PDF"

        with patch("app.utils.pdf_generator.HTML") as mock_HTML:
            mock_HTML.return_value = mock_html_instance
            from app.utils.pdf_generator import generate_tailored_pdf
            generate_tailored_pdf(
                job_title="Engineer",
                company="Corp",
                candidate_name="Jane",
                tailored_bullets=["Did things"],
                cover_letter="Dear...",
            )

        call_kwargs = mock_HTML.call_args
        assert "string" in call_kwargs.kwargs or len(call_kwargs.args) > 0
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_pdf_generator.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Create `app/templates/pdf_resume.html`**

This is the HTML that WeasyPrint renders to PDF. It is NOT a Jinja2 FastAPI template — it's rendered via `jinja2.Environment` directly in code.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<style>
  @page { margin: 2cm; size: A4; }
  body { font-family: 'Georgia', serif; font-size: 11pt; color: #1a1a1a; line-height: 1.5; }
  h1 { font-size: 20pt; margin-bottom: 2pt; }
  h2 { font-size: 13pt; border-bottom: 1px solid #6366f1; color: #6366f1;
       padding-bottom: 3pt; margin-top: 18pt; margin-bottom: 8pt; }
  .meta { color: #555; font-size: 10pt; margin-bottom: 16pt; }
  ul { margin: 0; padding-left: 18pt; }
  li { margin-bottom: 5pt; }
  .cover-letter { margin-top: 24pt; white-space: pre-wrap; }
  .page-break { page-break-before: always; }
</style>
</head>
<body>

<h1>{{ candidate_name }}</h1>
<div class="meta">Tailored application for <strong>{{ job_title }}</strong> at <strong>{{ company }}</strong></div>

<h2>Relevant Experience Highlights</h2>
<ul>
  {% for bullet in tailored_bullets %}
  <li>{{ bullet }}</li>
  {% endfor %}
</ul>

<div class="page-break"></div>

<h2>Cover Letter</h2>
<div class="cover-letter">{{ cover_letter }}</div>

</body>
</html>
```

- [ ] **Step 4: Implement `app/utils/pdf_generator.py`**

```python
from jinja2 import Environment, FileSystemLoader
from pathlib import Path
from weasyprint import HTML

_TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"
_env = Environment(loader=FileSystemLoader(str(_TEMPLATE_DIR)))


def generate_tailored_pdf(
    job_title: str,
    company: str,
    candidate_name: str,
    tailored_bullets: list[str],
    cover_letter: str,
) -> bytes:
    template = _env.get_template("pdf_resume.html")
    html_string = template.render(
        job_title=job_title,
        company=company,
        candidate_name=candidate_name,
        tailored_bullets=tailored_bullets,
        cover_letter=cover_letter,
    )
    return HTML(string=html_string).write_pdf()
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
pytest tests/test_pdf_generator.py -v
```

Expected: Both tests PASS.

- [ ] **Step 6: Commit**

```bash
git add app/utils/pdf_generator.py app/templates/pdf_resume.html tests/test_pdf_generator.py
git commit -m "feat: WeasyPrint PDF generator for tailored resume + cover letter"
```

---

## Task 4: Tailor Route

**Files:**
- Create: `app/routes/tailor.py`

- [ ] **Step 1: Implement `app/routes/tailor.py`**

```python
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.auth import get_current_user, supabase
from app.utils.resume_tailor import tailor_for_job
from app.utils.pdf_generator import generate_tailored_pdf
from datetime import datetime, timezone

router = APIRouter()


@router.post("/{job_id}/generate")
async def generate_tailored_docs(
    job_id: int,
    user=Depends(get_current_user),
):
    """Generate tailored resume bullets + cover letter for a job, cache in DB."""
    profile = (
        supabase.table("profiles")
        .select("resume_text, full_name")
        .eq("id", user["id"])
        .single()
        .execute()
    )
    resume_text = (profile.data or {}).get("resume_text") or ""
    if not resume_text:
        raise HTTPException(status_code=400, detail="Upload your resume first")

    job_resp = (
        supabase.table("jobs")
        .select("title, company, description")
        .eq("id", job_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not job_resp.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_resp.data[0]
    job_description = job.get("description") or ""
    if not job_description:
        raise HTTPException(status_code=422, detail="Fetch the job description first")

    result = tailor_for_job(
        resume_text=resume_text,
        job_description=job_description,
        job_title=job["title"],
        company=job["company"],
    )

    bullets_text = "\n".join(f"• {b}" for b in result["tailored_bullets"])
    supabase.table("jobs").update({
        "tailored_resume": bullets_text,
        "cover_letter": result["cover_letter"],
        "tailored_at": datetime.now(timezone.utc).isoformat(),
    }).eq("id", job_id).execute()

    return {
        "success": True,
        "tailored_bullets": result["tailored_bullets"],
        "cover_letter": result["cover_letter"],
    }


@router.get("/{job_id}/download-pdf")
async def download_tailored_pdf(
    job_id: int,
    user=Depends(get_current_user),
):
    """Download previously generated tailored docs as a PDF."""
    profile = (
        supabase.table("profiles")
        .select("full_name")
        .eq("id", user["id"])
        .single()
        .execute()
    )
    candidate_name = (profile.data or {}).get("full_name") or user.get("email", "Candidate")

    job_resp = (
        supabase.table("jobs")
        .select("title, company, tailored_resume, cover_letter")
        .eq("id", job_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not job_resp.data:
        raise HTTPException(status_code=404, detail="Job not found")

    job = job_resp.data[0]
    if not job.get("tailored_resume"):
        raise HTTPException(status_code=422, detail="Generate tailored docs first")

    bullets = [b.lstrip("• ").strip() for b in job["tailored_resume"].split("\n") if b.strip()]

    pdf_bytes = generate_tailored_pdf(
        job_title=job["title"],
        company=job["company"],
        candidate_name=candidate_name,
        tailored_bullets=bullets,
        cover_letter=job["cover_letter"],
    )

    filename = f"resume_{job['company'].replace(' ', '_')}_{job['title'].replace(' ', '_')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
```

- [ ] **Step 2: Wire into `app/main.py`**

Add import and router:

```python
from app.routes import auth, dashboard, jobs, search, resume, tailor

app.include_router(tailor.router, prefix="/tailor", tags=["Tailor"])
```

- [ ] **Step 3: Commit**

```bash
git add app/routes/tailor.py app/main.py
git commit -m "feat: tailor route — generate tailored docs + PDF download"
```

---

## Task 5: Add "Tailor & Download" Buttons to Job Board

**Files:**
- Modify: `app/templates/jobs.html`

- [ ] **Step 1: Add buttons to expanded job detail section in `jobs.html`**

Inside each job card's expanded detail area, after the existing action buttons, add:

```html
<!-- Tailor & Download -->
<div class="mt-3 d-flex gap-2 flex-wrap">
    {% if job.tailored_resume %}
    <a href="/tailor/{{ job.id }}/download-pdf" class="btn btn-sm btn-zephyr">
        <i class="bi bi-file-earmark-pdf me-1"></i>Download PDF
    </a>
    <button class="btn btn-sm btn-zephyr-secondary" onclick="tailorJob({{ job.id }})">
        <i class="bi bi-arrow-repeat me-1"></i>Re-tailor
    </button>
    {% else %}
    <button class="btn btn-sm btn-zephyr" onclick="tailorJob({{ job.id }})" id="tailor-btn-{{ job.id }}">
        <i class="bi bi-magic me-1"></i>Tailor Resume
    </button>
    {% endif %}
</div>
{% if job.tailored_resume %}
<div class="mt-2 p-2 rounded" style="background:#f8fafc;font-size:0.85rem;">
    <strong>Tailored bullets:</strong><br>
    {{ job.tailored_resume | replace('\n', '<br>') | safe }}
</div>
{% endif %}
```

- [ ] **Step 2: Add the `tailorJob` JavaScript function**

At the bottom of `jobs.html`, before `{% endblock %}`:

```html
<script>
async function tailorJob(jobId) {
    const btn = document.getElementById('tailor-btn-' + jobId);
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner-border spinner-border-sm me-1"></span>Tailoring...';
    }
    try {
        const resp = await fetch('/tailor/' + jobId + '/generate', {method: 'POST'});
        if (resp.ok) {
            window.location.reload();
        } else {
            const data = await resp.json();
            alert('Error: ' + (data.detail || 'Unknown error'));
            if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-magic me-1"></i>Tailor Resume'; }
        }
    } catch (e) {
        alert('Network error — try again');
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-magic me-1"></i>Tailor Resume'; }
    }
}
</script>
```

- [ ] **Step 3: Smoke test**

Start the app, go to a job that has a description, click "Tailor Resume". After a few seconds the page reloads showing tailored bullets and a "Download PDF" link. Click it and verify a PDF downloads.

- [ ] **Step 4: Commit**

```bash
git add app/templates/jobs.html
git commit -m "feat: tailor and download PDF buttons on job cards"
```

---

## Self-Review

**Spec coverage:**
- ✅ LLM rewrites bullets → `resume_tailor.py` `tailor_for_job()`
- ✅ LLM generates cover letter → same function, same response
- ✅ Output as PDF → `pdf_generator.py` + `pdf_resume.html`
- ✅ Per-job tailoring → cached in `jobs.tailored_resume` + `jobs.cover_letter`
- ✅ Download from dashboard → `/tailor/{id}/download-pdf`

**No placeholders:** All steps have actual code. ✅

**Type consistency:**
- `tailor_for_job()` returns `{"tailored_bullets": list[str], "cover_letter": str}` — used in tailor.py Task 4 ✅
- `generate_tailored_pdf(job_title, company, candidate_name, tailored_bullets, cover_letter)` — matches template variables ✅
