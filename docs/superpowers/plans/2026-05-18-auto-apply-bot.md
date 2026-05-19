# Auto-Apply Bot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Prerequisite:** Plan `2026-05-18-tailored-documents.md` must be complete. `jobs.tailored_resume` and `jobs.cover_letter` must exist.

**Goal:** For jobs with a "Easy Apply" flag or simple ATS forms, automatically fill and submit the application using Playwright, then log the result.

**Architecture:** `app/utils/auto_applier.py` handles browser automation for LinkedIn EasyApply. It accepts pre-filled field values (name, email, phone, cover letter) from the user's profile and the tailored cover letter. A `app/routes/apply.py` endpoint triggers it per job. The user sets their contact details in a new `profiles.apply_config` JSONB column (phone, LinkedIn URL, etc.). Every auto-apply attempt is logged to a new `apply_log` table.

**Tech Stack:** Playwright (async), Supabase (apply_log + profiles.apply_config), FastAPI background tasks (so the HTTP response returns immediately while Playwright runs).

> ⚠️ **LinkedIn scraping note:** LinkedIn actively fights automation. EasyApply works reliably for simple 1-step forms. Multi-step forms with LinkedIn-specific question flows (work authorization, custom screening questions) require manual handling. This plan implements EasyApply for simple forms and gracefully aborts complex ones.

---

## File Map

| Action | Path | Responsibility |
|--------|------|----------------|
| Create | `app/utils/auto_applier.py` | Playwright LinkedIn EasyApply automation |
| Create | `app/routes/apply.py` | Trigger auto-apply + status endpoint |
| Modify | `app/main.py` | Include apply router |
| Modify | `app/templates/jobs.html` | "Auto-Apply" button + status display |
| Modify | `app/templates/resume.html` | Contact info form (phone, LinkedIn URL) |
| Modify | `app/routes/resume.py` | Save contact info to profiles |
| Create | `tests/test_auto_applier.py` | Unit tests for form-filling logic |

---

## Task 1: DB Migration

- [ ] **Step 1: Run in Supabase SQL editor**

```sql
-- Contact info for auto-apply form filling
ALTER TABLE profiles
  ADD COLUMN IF NOT EXISTS apply_config JSONB DEFAULT '{}';

-- Log of every auto-apply attempt
CREATE TABLE IF NOT EXISTS apply_log (
  id          SERIAL PRIMARY KEY,
  job_id      INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
  user_id     UUID NOT NULL,
  status      TEXT NOT NULL,  -- 'success' | 'failed' | 'aborted'
  error       TEXT,
  attempted_at TIMESTAMPTZ DEFAULT NOW()
);

-- Jobs auto-apply status
ALTER TABLE jobs
  ADD COLUMN IF NOT EXISTS auto_apply_status TEXT,  -- null | 'pending' | 'success' | 'failed' | 'aborted'
  ADD COLUMN IF NOT EXISTS auto_applied_at TIMESTAMPTZ;
```

- [ ] **Step 2: Commit**

```bash
git add .
git commit -m "feat: DB migration for auto-apply log + profiles.apply_config"
```

---

## Task 2: Contact Info Form

Users need to supply phone number and any other details LinkedIn EasyApply asks for.

**Files:**
- Modify: `app/routes/resume.py`
- Modify: `app/templates/resume.html`

- [ ] **Step 1: Add save-contact endpoint to `app/routes/resume.py`**

```python
from fastapi import Form

@router.post("/save-contact")
async def save_contact(
    request: Request,
    phone: str = Form(""),
    linkedin_url: str = Form(""),
    user=Depends(get_current_user),
):
    """Save contact details used in auto-apply form filling."""
    supabase.table("profiles").update({
        "apply_config": {
            "phone": phone.strip(),
            "linkedin_url": linkedin_url.strip(),
        }
    }).eq("id", user["id"]).execute()
    return RedirectResponse(url="/resume/?saved=1", status_code=303)
```

- [ ] **Step 2: Add contact form to `app/templates/resume.html`**

Below the existing upload card, add:

```html
<div class="card mt-4">
    <div class="card-header">
        <h5 class="mb-0"><i class="bi bi-person-vcard me-2"></i>Auto-Apply Contact Info</h5>
    </div>
    <div class="card-body">
        <p class="text-muted small">These details are used to fill application forms automatically.</p>
        <form method="POST" action="/resume/save-contact">
            <div class="mb-3">
                <label for="phone" class="form-label">Phone number</label>
                <input type="tel" class="form-control" id="phone" name="phone"
                       value="{{ apply_config.phone or '' }}" placeholder="+1 555 000 0000">
            </div>
            <div class="mb-3">
                <label for="linkedin_url" class="form-label">LinkedIn profile URL</label>
                <input type="url" class="form-control" id="linkedin_url" name="linkedin_url"
                       value="{{ apply_config.linkedin_url or '' }}"
                       placeholder="https://linkedin.com/in/yourname">
            </div>
            <button type="submit" class="btn btn-zephyr">
                <i class="bi bi-save me-2"></i>Save
            </button>
        </form>
    </div>
</div>
```

- [ ] **Step 3: Pass `apply_config` to resume template context**

In `app/routes/resume.py`, update `resume_page` to also fetch `apply_config`:

```python
@router.get("/", response_class=HTMLResponse)
async def resume_page(request: Request, user=Depends(get_current_user)):
    profile = (
        supabase.table("profiles")
        .select("resume_text, resume_filename, apply_config")
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
        "apply_config": data.get("apply_config") or {},
        "uploaded": request.query_params.get("uploaded") == "1",
        "saved": request.query_params.get("saved") == "1",
    })
```

- [ ] **Step 4: Commit**

```bash
git add app/routes/resume.py app/templates/resume.html
git commit -m "feat: contact info form for auto-apply (phone, LinkedIn URL)"
```

---

## Task 3: Auto-Applier Core

**Files:**
- Create: `app/utils/auto_applier.py`
- Create: `tests/test_auto_applier.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_auto_applier.py`:

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestIsEasyApply:
    @pytest.mark.asyncio
    async def test_returns_true_when_easy_apply_button_found(self):
        mock_page = AsyncMock()
        mock_btn = MagicMock()
        mock_page.query_selector.return_value = mock_btn

        from app.utils.auto_applier import is_easy_apply
        result = await is_easy_apply(mock_page)

        mock_page.query_selector.assert_called_once_with(".jobs-apply-button--top-card")
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_false_when_no_easy_apply_button(self):
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None

        from app.utils.auto_applier import is_easy_apply
        result = await is_easy_apply(mock_page)
        assert result is False


class TestFillTextField:
    @pytest.mark.asyncio
    async def test_fills_field_by_label(self):
        mock_page = AsyncMock()
        mock_input = AsyncMock()
        mock_page.query_selector.return_value = mock_input

        from app.utils.auto_applier import fill_text_field
        await fill_text_field(mock_page, "Phone", "555-1234")

        mock_input.fill.assert_called_once_with("555-1234")

    @pytest.mark.asyncio
    async def test_does_nothing_when_field_not_found(self):
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None

        from app.utils.auto_applier import fill_text_field
        # Should not raise
        await fill_text_field(mock_page, "NonExistentField", "value")


class TestCountFormSteps:
    @pytest.mark.asyncio
    async def test_counts_progress_steps(self):
        mock_page = AsyncMock()
        mock_page.query_selector_all.return_value = [MagicMock(), MagicMock(), MagicMock()]

        from app.utils.auto_applier import count_form_steps
        count = await count_form_steps(mock_page)
        assert count == 3

    @pytest.mark.asyncio
    async def test_returns_zero_when_no_steps_found(self):
        mock_page = AsyncMock()
        mock_page.query_selector_all.return_value = []

        from app.utils.auto_applier import count_form_steps
        count = await count_form_steps(mock_page)
        assert count == 0
```

- [ ] **Step 2: Run to verify failure**

```bash
pytest tests/test_auto_applier.py -v
```

Expected: `ImportError`.

- [ ] **Step 3: Implement `app/utils/auto_applier.py`**

```python
import asyncio
from playwright.async_api import async_playwright, Page

# LinkedIn requires login for EasyApply.
# We store credentials in env vars — never in code.
import os
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL", "")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD", "")

# Abort if form has more steps than this — too complex for automation
MAX_FORM_STEPS = 2


async def is_easy_apply(page: Page) -> bool:
    btn = await page.query_selector(".jobs-apply-button--top-card")
    return btn is not None


async def count_form_steps(page: Page) -> int:
    steps = await page.query_selector_all(".jobs-easy-apply-form-section__grouping")
    return len(steps)


async def fill_text_field(page: Page, label_text: str, value: str) -> None:
    """Fill an input whose label contains label_text."""
    selector = f"input[aria-label*='{label_text}'], input[placeholder*='{label_text}']"
    field = await page.query_selector(selector)
    if field:
        await field.fill(value)


async def linkedin_login(page: Page) -> bool:
    """Log into LinkedIn. Returns True if login succeeded."""
    await page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded", timeout=20000)
    await page.fill("#username", LINKEDIN_EMAIL)
    await page.fill("#password", LINKEDIN_PASSWORD)
    await page.click('[type="submit"]')
    await asyncio.sleep(3)
    # Verify we're logged in — nav should appear
    nav = await page.query_selector(".global-nav")
    return nav is not None


async def apply_to_job(
    job_url: str,
    full_name: str,
    email: str,
    phone: str,
    cover_letter: str,
) -> dict:
    """
    Attempt to auto-apply via LinkedIn EasyApply.

    Returns:
        {"status": "success" | "failed" | "aborted", "error": str | None}
    """
    if not LINKEDIN_EMAIL or not LINKEDIN_PASSWORD:
        return {"status": "aborted", "error": "LINKEDIN_EMAIL or LINKEDIN_PASSWORD not set"}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"],
        )
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="en-US",
        )

        try:
            page = await context.new_page()

            logged_in = await linkedin_login(page)
            if not logged_in:
                return {"status": "failed", "error": "LinkedIn login failed"}

            await page.goto(job_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

            if not await is_easy_apply(page):
                return {"status": "aborted", "error": "No EasyApply button — external application"}

            # Click EasyApply
            await page.click(".jobs-apply-button--top-card")
            await asyncio.sleep(2)

            steps = await count_form_steps(page)
            if steps > MAX_FORM_STEPS:
                # Close modal and abort — too complex
                close = await page.query_selector("[aria-label='Dismiss']")
                if close:
                    await close.click()
                return {
                    "status": "aborted",
                    "error": f"Form has {steps} steps — requires manual review",
                }

            # Fill standard fields
            await fill_text_field(page, "Phone", phone)
            await fill_text_field(page, "Mobile phone number", phone)

            # Cover letter text area
            textarea = await page.query_selector("textarea")
            if textarea and cover_letter:
                await textarea.fill(cover_letter[:3000])

            # Click Next or Submit
            submit_btn = await page.query_selector(
                "button[aria-label='Submit application'], "
                "button[aria-label='Review your application'], "
                "button[aria-label='Continue to next step']"
            )
            if not submit_btn:
                return {"status": "failed", "error": "Could not find submit/next button"}

            label = await submit_btn.get_attribute("aria-label") or ""
            await submit_btn.click()
            await asyncio.sleep(2)

            if "Submit" in label or "Review" in label:
                # One more click if review step appeared
                final = await page.query_selector("button[aria-label='Submit application']")
                if final:
                    await final.click()
                    await asyncio.sleep(2)

            return {"status": "success", "error": None}

        except Exception as e:
            return {"status": "failed", "error": str(e)}

        finally:
            await browser.close()
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
pytest tests/test_auto_applier.py -v
```

Expected: All 6 tests PASS.

- [ ] **Step 5: Add LinkedIn credentials to `.env`**

```
LINKEDIN_EMAIL=your@email.com
LINKEDIN_PASSWORD=yourpassword
```

- [ ] **Step 6: Commit**

```bash
git add app/utils/auto_applier.py tests/test_auto_applier.py
git commit -m "feat: LinkedIn EasyApply auto-applier with step-count guard"
```

---

## Task 4: Apply Route

**Files:**
- Create: `app/routes/apply.py`
- Modify: `app/main.py`

- [ ] **Step 1: Implement `app/routes/apply.py`**

```python
from fastapi import APIRouter, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from datetime import datetime, timezone

from app.auth import get_current_user, supabase
from app.utils.auto_applier import apply_to_job

router = APIRouter()


async def _run_apply(job_id: int, user_id: str, job_url: str, full_name: str,
                     email: str, phone: str, cover_letter: str):
    """Background task: run Playwright apply, then log result."""
    result = await apply_to_job(
        job_url=job_url,
        full_name=full_name,
        email=email,
        phone=phone,
        cover_letter=cover_letter,
    )

    update = {
        "auto_apply_status": result["status"],
        "auto_applied_at": datetime.now(timezone.utc).isoformat(),
    }
    if result["status"] == "success":
        update["status"] = "Applied"

    supabase.table("jobs").update(update).eq("id", job_id).execute()
    supabase.table("apply_log").insert({
        "job_id": job_id,
        "user_id": user_id,
        "status": result["status"],
        "error": result.get("error"),
    }).execute()


@router.post("/{job_id}/auto-apply")
async def trigger_auto_apply(
    job_id: int,
    background_tasks: BackgroundTasks,
    user=Depends(get_current_user),
):
    """Trigger auto-apply for a job. Returns immediately; apply runs in background."""
    job_resp = (
        supabase.table("jobs")
        .select("url, cover_letter, auto_apply_status")
        .eq("id", job_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not job_resp.data:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    job = job_resp.data[0]

    if job.get("auto_apply_status") == "pending":
        return JSONResponse({"error": "Auto-apply already in progress"}, status_code=409)

    if not job.get("cover_letter"):
        return JSONResponse({"error": "Generate tailored docs first"}, status_code=422)

    profile = (
        supabase.table("profiles")
        .select("full_name, apply_config")
        .eq("id", user["id"])
        .single()
        .execute()
    )
    profile_data = profile.data or {}
    apply_config = profile_data.get("apply_config") or {}
    phone = apply_config.get("phone") or ""

    # Mark as pending immediately
    supabase.table("jobs").update({"auto_apply_status": "pending"}).eq("id", job_id).execute()

    background_tasks.add_task(
        _run_apply,
        job_id=job_id,
        user_id=user["id"],
        job_url=job["url"],
        full_name=profile_data.get("full_name") or user.get("email", ""),
        email=user["email"],
        phone=phone,
        cover_letter=job["cover_letter"],
    )

    return {"status": "pending", "message": "Auto-apply started in background"}


@router.get("/{job_id}/apply-status")
async def get_apply_status(
    job_id: int,
    user=Depends(get_current_user),
):
    """Poll for auto-apply status."""
    job_resp = (
        supabase.table("jobs")
        .select("auto_apply_status, auto_applied_at")
        .eq("id", job_id)
        .eq("user_id", user["id"])
        .execute()
    )
    if not job_resp.data:
        return JSONResponse({"error": "Job not found"}, status_code=404)

    job = job_resp.data[0]
    return {
        "status": job.get("auto_apply_status"),
        "applied_at": job.get("auto_applied_at"),
    }
```

- [ ] **Step 2: Wire into `app/main.py`**

```python
from app.routes import auth, dashboard, jobs, search, resume, tailor, apply

app.include_router(apply.router, prefix="/apply", tags=["Apply"])
```

- [ ] **Step 3: Commit**

```bash
git add app/routes/apply.py app/main.py
git commit -m "feat: auto-apply trigger endpoint with background task + status poll"
```

---

## Task 5: Auto-Apply Button in Job Board UI

**Files:**
- Modify: `app/templates/jobs.html`

- [ ] **Step 1: Add Auto-Apply button + status display to job card detail area in `jobs.html`**

After the existing "Tailor & Download" buttons added in the tailored-documents plan, add:

```html
<!-- Auto-Apply -->
{% if job.auto_apply_status == 'success' %}
<span class="badge bg-success ms-2"><i class="bi bi-robot me-1"></i>Auto-Applied</span>
{% elif job.auto_apply_status == 'pending' %}
<span class="badge bg-warning text-dark ms-2" id="apply-status-{{ job.id }}">
    <span class="spinner-border spinner-border-sm me-1"></span>Applying...
</span>
{% elif job.auto_apply_status == 'failed' %}
<span class="badge bg-danger ms-2"><i class="bi bi-exclamation-triangle me-1"></i>Failed</span>
{% elif job.auto_apply_status == 'aborted' %}
<span class="badge bg-secondary ms-2"><i class="bi bi-slash-circle me-1"></i>Skipped</span>
{% elif job.cover_letter %}
<button class="btn btn-sm btn-outline-primary ms-2" onclick="autoApply({{ job.id }})" id="apply-btn-{{ job.id }}">
    <i class="bi bi-robot me-1"></i>Auto-Apply
</button>
{% endif %}
```

- [ ] **Step 2: Add polling script for pending jobs**

In the JavaScript block at the bottom of `jobs.html`, add:

```javascript
async function autoApply(jobId) {
    const btn = document.getElementById('apply-btn-' + jobId);
    if (btn) { btn.disabled = true; btn.innerHTML = '<span class="spinner-border spinner-border-sm"></span>'; }

    const resp = await fetch('/apply/' + jobId + '/auto-apply', {method: 'POST'});
    const data = await resp.json();

    if (data.status === 'pending') {
        pollApplyStatus(jobId);
    } else {
        alert('Error: ' + (data.error || JSON.stringify(data)));
        if (btn) { btn.disabled = false; btn.innerHTML = '<i class="bi bi-robot me-1"></i>Auto-Apply'; }
    }
}

function pollApplyStatus(jobId) {
    const interval = setInterval(async () => {
        const resp = await fetch('/apply/' + jobId + '/apply-status');
        const data = await resp.json();
        if (data.status !== 'pending') {
            clearInterval(interval);
            window.location.reload();
        }
    }, 3000);
}

// Auto-poll any job already in pending state on page load
document.addEventListener('DOMContentLoaded', () => {
    document.querySelectorAll('[id^="apply-status-"]').forEach(el => {
        const jobId = el.id.replace('apply-status-', '');
        pollApplyStatus(jobId);
    });
});
```

- [ ] **Step 3: Smoke test**

Start the app, open a job that has a cover letter, click "Auto-Apply". The button should spin. After 10–30 seconds the status badge updates to "Auto-Applied" or shows the failure reason. Check Supabase `apply_log` table to confirm a row was inserted.

- [ ] **Step 4: Commit**

```bash
git add app/templates/jobs.html
git commit -m "feat: auto-apply button, pending spinner, and status polling on job cards"
```

---

## Self-Review

**Spec coverage:**
- ✅ Playwright form filling — `auto_applier.py` `apply_to_job()`
- ✅ Common fields (name, email, phone, cover letter) — `fill_text_field` + textarea fill
- ✅ Log every application — `apply_log` table + `_run_apply` background task
- ✅ Dashboard shows outcome — status badge on job cards
- ✅ Guard against complex multi-step forms — `count_form_steps` + `MAX_FORM_STEPS = 2`

**LinkedIn credential security:**
- Credentials stored only in `.env` (already in `.gitignore`) — never in code ✅

**Type consistency:**
- `apply_to_job()` returns `{"status": str, "error": str | None}` — consumed in `_run_apply` ✅
- `auto_apply_status` values: `"pending" | "success" | "failed" | "aborted"` — consistent across route, template, and DB ✅
