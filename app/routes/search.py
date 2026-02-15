"""
Search configuration routes
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
async def list_searches(request: Request, user = Depends(get_current_user)):
    """View and manage search configurations"""
    
    try:
        response = supabase.table("search_configs").select("*").eq("user_id", user["id"]).execute()
        configs = response.data or []
        
        return templates.TemplateResponse("search_configs.html", {
            "request": request,
            "user": user,
            "configs": configs
        })
        
    except Exception as e:
        return templates.TemplateResponse("search_configs.html", {
            "request": request,
            "user": user,
            "error": f"Error loading configs: {str(e)}"
        })


@router.post("/create")
async def create_search(
    request: Request,
    keywords: str = Form(...),
    location: str = Form(...),
    is_remote: bool = Form(False),
    experience_level: str = Form(None),
    pages: int = Form(2),
    user = Depends(get_current_user)
):
    """Create new search configuration"""
    
    try:
        supabase.table("search_configs").insert({
            "user_id": user["id"],
            "keywords": keywords,
            "location": location,
            "is_remote": is_remote,
            "experience_level": experience_level if experience_level else None,
            "pages": pages,
            "is_active": True
        }).execute()
        
        return RedirectResponse(url="/search", status_code=303)
        
    except Exception as e:
        return {"error": str(e)}


@router.post("/{config_id}/toggle")
async def toggle_search(
    request: Request,
    config_id: int,
    user = Depends(get_current_user)
):
    """Toggle search config active status"""
    
    try:
        # Get current status
        response = supabase.table("search_configs").select("is_active").eq("id", config_id).eq("user_id", user["id"]).execute()
        
        if response.data:
            current_status = response.data[0]["is_active"]
            # Toggle it
            supabase.table("search_configs").update({"is_active": not current_status}).eq("id", config_id).execute()
        
        return RedirectResponse(url="/search", status_code=303)
        
    except Exception as e:
        return {"error": str(e)}


@router.post("/{config_id}/delete")
async def delete_search(
    request: Request,
    config_id: int,
    user = Depends(get_current_user)
):
    """Delete search configuration"""
    
    try:
        supabase.table("search_configs").delete().eq("id", config_id).eq("user_id", user["id"]).execute()
        return RedirectResponse(url="/search", status_code=303)
        
    except Exception as e:
        return {"error": str(e)}
