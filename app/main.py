"""
Zephyr - FastAPI Job Application Tracker
Multi-user with Supabase authentication
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import os
from pathlib import Path

from app.auth import get_current_user, supabase
from app.routes import auth, dashboard, jobs, search

# App initialization
app = FastAPI(
    title="Zephyr Job Tracker",
    description="Automated job application tracking with LinkedIn scraping",
    version="2.0.0"
)

# Session middleware for cookie-based auth
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this-in-production")
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Mount static files (CSS, JS, images)
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])
app.include_router(jobs.router, prefix="/job-board", tags=["Job Board"])
app.include_router(search.router, prefix="/search", tags=["Search Configs"])


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Landing page - redirect to dashboard if logged in, else login"""
    user = request.session.get("user")
    if user:
        return RedirectResponse(url="/dashboard")
    return RedirectResponse(url="/auth/login")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "app": "zephyr"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
