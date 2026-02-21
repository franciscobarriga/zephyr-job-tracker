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


def calculate_level(applied_count: int) -> tuple:
    """Calculate user level and XP progress based on applied jobs"""
    # Level thresholds
    thresholds = [0, 5, 10, 20, 35, 50, 75, 100, 150, 200]
    level = 1

    for i, threshold in enumerate(thresholds):
        if applied_count >= threshold:
            level = i + 1

    # Calculate XP for next level
    next_threshold = thresholds[level] if level < len(thresholds) else thresholds[-1] + 50
    current_threshold = thresholds[level - 1]
    xp_in_level = applied_count - current_threshold
    xp_needed = next_threshold - current_threshold
    xp_progress = int((xp_in_level / xp_needed) * 100) if xp_needed > 0 else 100

    return level, xp_progress


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
        thinking_count = len([j for j in jobs if j.get("status") == "Thinking"])
        ignored_count = len([j for j in jobs if j.get("status") == "Ignored"])
        new_count = len([j for j in jobs if j.get("status") == "New" or not j.get("status")])
        active_searches = len([c for c in configs if c.get("is_active")])

        # Jobs this week
        week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        recent_jobs = [j for j in jobs if j.get("created_at", "") >= week_ago]
        week_count = len(recent_jobs)

        # Recent applications (last 10) - Only Applied jobs, sorted by applied date
        applied_jobs = [j for j in jobs if j.get("status") == "Applied"]
        sorted_jobs = sorted(applied_jobs, key=lambda x: x.get("applied_at", x.get("created_at", "")), reverse=True)[:10]

        # Gamification - Calculate level and XP
        user_level, xp_progress = calculate_level(applied_count)

        # Streak calculation - use applied_at for accurate tracking
        user_streak = 0
        if applied_count > 0:
            # Count consecutive days with applications using applied_at
            dates_with_applications = set()
            for job in jobs:
                if job.get("status") == "Applied":
                    # Use applied_at if available, otherwise fallback to created_at
                    date = job.get("applied_at", job.get("created_at", ""))[:10]
                    if date:
                        dates_with_applications.add(date)

            if dates_with_applications:
                sorted_dates = sorted(dates_with_applications, reverse=True)
                today = datetime.now().date().isoformat()

                # Check if user applied today or yesterday
                if sorted_dates[0] == today or sorted_dates[0] == (datetime.now() - timedelta(days=1)).date().isoformat():
                    streak = 1
                    check_date = datetime.fromisoformat(sorted_dates[0])
                    for i in range(1, len(sorted_dates)):
                        prev_date = (check_date - timedelta(days=i)).date().isoformat()
                        if prev_date in sorted_dates:
                            streak += 1
                        else:
                            break
                    user_streak = streak

        # Get username from user metadata
        username = user.get("user_metadata", {}).get("username", user.get("email", "").split("@")[0])

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "username": username,
            "stats": {
                "total": total_jobs,
                "applied": applied_count,
                "thinking": thinking_count,
                "ignored": ignored_count,
                "new": new_count,
                "active_searches": active_searches,
                "week": week_count
            },
            "recent_jobs": sorted_jobs,
            "user_level": user_level,
            "xp_progress": xp_progress,
            "user_streak": user_streak
        })

    except Exception as e:
        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "user": user,
            "error": f"Error loading dashboard: {str(e)}"
        })
