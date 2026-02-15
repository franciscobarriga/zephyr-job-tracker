"""
Dashboard routes
"""

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path
from datetime import datetime, timedelta

from app.auth import get_current_user, supabase

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, user = Depends(get_current_user)):
    """Main dashboard view with stats"""
    
    try:
        # Fetch user's jobs
        jobs_response = supabase.table("jobs").select("*").eq("user_id", user["id"]).execute()
        jobs = jobs_response.data or []
        
        # Fetch search configs
        configs_response = supabase.table("search_configs").select("*").eq("user_id", user["id"]).execute()
        configs = configs_response.data or []
        
        # Calculate stats
        total_jobs = len(jobs)
        applied_count = len([j for j in jobs if j.get("status") == "Applied"])
        active_searches = len([c for c in configs if c.get("is_active")])
        
        # Jobs this week
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_jobs = [j for j in jobs if j.get("created_at", "") >= week_ago]
        week_count = len(recent_jobs)
        
        # Recent applications (last 10)
        sorted_jobs = sorted(jobs, key=lambda x: x.get("created_at", ""), reverse=True)[:10]
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "stats": {
                "total": total_jobs,
                "applied": applied_count,
                "active_searches": active_searches,
                "week": week_count
            },
            "recent_jobs": sorted_jobs
        })
        
    except Exception as e:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "error": f"Error loading dashboard: {str(e)}"
        })
