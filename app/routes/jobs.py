"""
Jobs management routes
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import get_current_user, supabase

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def list_jobs(request: Request, user = Depends(get_current_user)):
    """View all job applications"""
    
    try:
        response = supabase.table("jobs").select("*").eq("user_id", user["id"]).execute()
        jobs = response.data or []
        
        # Sort by created date
        jobs = sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)
        
        return templates.TemplateResponse("jobs.html", {
            "request": request,
            "user": user,
            "jobs": jobs
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
        supabase.table("jobs").update({"status": status}).eq("id", job_id).eq("user_id", user["id"]).execute()
        return RedirectResponse(url="/jobs", status_code=303)
        
    except Exception as e:
        return {"error": str(e)}
