"""
Jobs management routes
"""

import os
import asyncio
import time
import logging
from fastapi import APIRouter, Request, Depends, Form, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

from app.auth import get_current_user, supabase

load_dotenv()

logger = logging.getLogger(__name__)
router = APIRouter()

# In-process scraper lock: prevents 5 friends spamming the button from
# kicking off 5 concurrent Chromium instances.
_SCRAPE_STATE = {"running": False, "last_started_at": 0.0, "started_by": None}
_SCRAPE_COOLDOWN_SEC = 300  # 5 minutes between runs


async def _run_scraper_inline(triggered_by_user_id: str):
    """Run scraper.main() in the same process. Set running flag for the UI."""
    import sys as _sys
    from pathlib import Path as _Path
    _root = str(_Path(__file__).resolve().parent.parent.parent)
    if _root not in _sys.path:
        _sys.path.insert(0, _root)
    import scraper as _scraper
    _SCRAPE_STATE["running"] = True
    _SCRAPE_STATE["last_started_at"] = time.time()
    _SCRAPE_STATE["started_by"] = triggered_by_user_id
    try:
        await _scraper.main()
    except Exception:
        logger.exception("Inline scraper run failed")
    finally:
        _SCRAPE_STATE["running"] = False

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))



_SORT_KEYS = {
    "match":   lambda j: (-(j.get("match_score") or -1), j.get("created_at", "")),
    "date":    lambda j: (-(_iso_rank(j.get("created_at"))),),
    "company": lambda j: ((j.get("company") or "").lower(), j.get("title") or ""),
}


def _iso_rank(s):
    """Big number that sorts newest-first when negated."""
    return int((s or "0").replace("-", "").replace(":", "").replace("T", "").replace(".", "")[:14] or 0)


@router.get("/", response_class=HTMLResponse)
async def list_jobs(
    request: Request,
    user = Depends(get_current_user),
    status_filter: str = Query(None),
    sort: str = Query("date"),
):
    """View all job applications"""

    try:
        response = supabase.table("jobs").select("*").eq("user_id", user["id"]).execute()
        all_jobs = response.data or []

        # Non-applied jobs (Applied lives on dashboard)
        jobs = [j for j in all_jobs if j.get("status") != "Applied"]

        if status_filter and status_filter != "all":
            jobs = [j for j in jobs if j.get("status") == status_filter]

        sort_key = _SORT_KEYS.get(sort, _SORT_KEYS["date"])
        jobs = sorted(jobs, key=sort_key)

        return templates.TemplateResponse(request, "jobs.html", {
            "user": user,
            "jobs": jobs,
            "status_filter": status_filter,
            "sort": sort,
            "stats": {
                "total": len(all_jobs),
                "applied": len([j for j in all_jobs if j.get("status") == "Applied"]),
                "thinking": len([j for j in all_jobs if j.get("status") == "Thinking"]),
                "ignored": len([j for j in all_jobs if j.get("status") == "Ignored"]),
                "new": len([j for j in all_jobs if j.get("status") != "Applied" and (j.get("status") == "New" or not j.get("status"))]),
            },
        })

    except Exception as e:
        return templates.TemplateResponse(request, "jobs.html", {
            "user": user,
            "error": f"Error loading jobs: {str(e)}",
        })


@router.post("/{job_id}/update-status")
async def update_job_status(
    request: Request,
    job_id: int,
    status: str = Form(...),
    user = Depends(get_current_user)
):
    """Update job application status"""

    try:
        # Ignored = hard delete immediately (user explicitly rejected)
        if status == "Ignored":
            supabase.table("jobs").delete().eq("id", job_id).eq("user_id", user["id"]).execute()
            return RedirectResponse(url="/job-board", status_code=303)

        # Build update data
        update_data = {"status": status, "last_viewed_at": datetime.utcnow().isoformat()}

        # If marking as Applied, track when it was applied
        if status == "Applied":
            update_data["applied_at"] = datetime.utcnow().isoformat()

        supabase.table("jobs").update(update_data).eq("id", job_id).eq("user_id", user["id"]).execute()
        return RedirectResponse(url="/job-board", status_code=303)

    except Exception as e:
        return {"error": str(e)}


@router.post("/{job_id}/view")
async def mark_job_viewed(job_id: int, user=Depends(get_current_user)):
    """Lightweight ping that records the user expanded/viewed this job."""
    supabase.table("jobs").update({
        "last_viewed_at": datetime.utcnow().isoformat(),
    }).eq("id", job_id).eq("user_id", user["id"]).execute()
    return {"ok": True}


@router.post("/cleanup-stale")
async def trigger_cleanup(user=Depends(get_current_user)):
    """Manually trigger stale-job cleanup for the current user."""
    from app.utils.cleanup import cleanup_stale_jobs
    result = cleanup_stale_jobs(supabase, user_id=user["id"])
    return result


@router.get("/scrape-status")
async def scrape_status(user=Depends(get_current_user)):
    """Lightweight polling endpoint. UI shows a banner while running."""
    elapsed = time.time() - _SCRAPE_STATE["last_started_at"]
    return {
        "running": _SCRAPE_STATE["running"],
        "cooldown_remaining": max(0, int(_SCRAPE_COOLDOWN_SEC - elapsed)) if not _SCRAPE_STATE["running"] else 0,
    }


@router.post("/scrape-now")
async def scrape_now(background_tasks: BackgroundTasks, user=Depends(get_current_user)):
    """Kick off scraper.main() as a background task. One run at a time."""
    if _SCRAPE_STATE["running"]:
        return JSONResponse(
            {"started": False, "reason": "Scraper already running. Check back in a few minutes."},
            status_code=409,
        )
    elapsed = time.time() - _SCRAPE_STATE["last_started_at"]
    if elapsed < _SCRAPE_COOLDOWN_SEC:
        wait = int(_SCRAPE_COOLDOWN_SEC - elapsed)
        return JSONResponse(
            {"started": False, "reason": f"Just ran. Try again in {wait // 60}m {wait % 60}s."},
            status_code=429,
        )
    background_tasks.add_task(_run_scraper_inline, user["id"])
    return {"started": True, "message": "Scraper started. Refresh in 5-15 minutes."}


# Note: on-demand fetch-description was removed. Descriptions are fetched
# by the scraper job (scraper.py:analyze_new_jobs) the same run they're
# discovered, so by the time the user sees a row it already has description,
# AI summary, and match score.
