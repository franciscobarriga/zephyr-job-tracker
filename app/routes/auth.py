"""
Authentication routes - Login, Signup, Logout
"""

from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import supabase

router = APIRouter()

BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@router.post("/login")
async def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...)
):
    """Handle login form submission"""
    try:
        response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        # Store user in session
        request.session["user"] = {
            "id": response.user.id,
            "email": response.user.email,
            "user_metadata": response.user.user_metadata
        }
        request.session["access_token"] = response.session.access_token
        
        return RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
        
    except Exception as e:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": f"Login failed: {str(e)}"},
            status_code=400
        )


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Display signup page"""
    return templates.TemplateResponse("signup.html", {"request": request})


@router.post("/signup")
async def signup(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    username: str = Form(...),
    full_name: str = Form(None)
):
    """Handle signup form submission"""
    try:
        # Validate password length
        if len(password) < 6:
            raise ValueError("Password must be at least 6 characters")
        
        # Sign up user
        response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "options": {
                "data": {
                    "username": username,
                    "full_name": full_name
                }
            }
        })
        
        # Create profile entry
        if response.user:
            supabase.table("profiles").insert({
                "id": response.user.id,
                "username": username,
                "full_name": full_name
            }).execute()
        
        return templates.TemplateResponse(
            "login.html",
            {
                "request": request,
                "success": "Account created! Please check your email to verify, then login."
            }
        )
        
    except Exception as e:
        return templates.TemplateResponse(
            "signup.html",
            {"request": request, "error": f"Signup failed: {str(e)}"},
            status_code=400
        )


@router.get("/logout")
async def logout(request: Request):
    """Logout user"""
    try:
        supabase.auth.sign_out()
    except:
        pass
    
    request.session.clear()
    return RedirectResponse(url="/auth/login", status_code=status.HTTP_303_SEE_OTHER)
