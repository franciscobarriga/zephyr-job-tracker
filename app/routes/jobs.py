"""
Jobs management routes
"""

from fastapi import APIRouter, Request, Depends, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime

from app.auth import get_current_user, supabase

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def list_jobs(request: Request, user = Depends(get_current_user), status_filter: str = Query(None)):
    """View all job applications"""

    try:
        # Fetch all jobs
        response = supabase.table("jobs").select("*").eq("user_id", user["id"]).execute()
        all_jobs = response.data or []

        # Filter out Applied jobs (they go to dashboard)
        jobs = [j for j in all_jobs if j.get("status") != "Applied"]

        # Apply status filter if provided
        if status_filter and status_filter != "all":
            jobs = [j for j in jobs if j.get("status") == status_filter]

        # Sort by created date (newest first) for non-applied jobs
        jobs = sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)

        # Calculate stats
        total_jobs = len(all_jobs)
        applied_count = len([j for j in all_jobs if j.get("status") == "Applied"])
        thinking_count = len([j for j in all_jobs if j.get("status") == "Thinking"])
        ignored_count = len([j for j in all_jobs if j.get("status") == "Ignored"])
        new_count = len([j for j in all_jobs if j.get("status") != "Applied" and (j.get("status") == "New" or not j.get("status"))])

        return templates.TemplateResponse("jobs.html", {
            "request": request,
            "user": user,
            "jobs": jobs,
            "status_filter": status_filter,
            "stats": {
                "total": total_jobs,
                "applied": applied_count,
                "thinking": thinking_count,
                "ignored": ignored_count,
                "new": new_count
            }
        })
        
    except Exception as e:
        return templates.TemplateResponse("jobs.html", {
            "request": request,
            "user": user,
            "error": f"Error loading jobs: {str(e)}"
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
        # Build update data
        update_data = {"status": status}

        # If marking as Applied, track when it was applied
        if status == "Applied":
            update_data["applied_at"] = datetime.utcnow().isoformat()

        supabase.table("jobs").update(update_data).eq("id", job_id).eq("user_id", user["id"]).execute()
        return RedirectResponse(url="/job-board", status_code=303)

    except Exception as e:
        return {"error": str(e)}
