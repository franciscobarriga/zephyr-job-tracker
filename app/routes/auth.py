"""
Authentication routes - Login, Signup, Logout, Password reset
"""

import os
from fastapi import APIRouter, Request, Form, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import supabase, supabase_admin


def _app_base_url(request: Request) -> str:
    """Public base URL for password-reset redirects (handles Railway proxy)."""
    return os.getenv("APP_BASE_URL") or str(request.base_url).rstrip("/")

router = APIRouter()

from app.templating import templates


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse(request, "login.html")


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
            request,
            "login.html",
            {"error": f"Login failed: {str(e)}"},
            status_code=400,
        )


@router.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    """Display signup page"""
    return templates.TemplateResponse(request, "signup.html")


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
        
        # Profile row is auto-created by the on_auth_user_created DB trigger
        # (see migration: auto_create_profile_on_signup). Trigger reads
        # username + full_name from raw_user_meta_data we passed above.
        
        return templates.TemplateResponse(
            request,
            "login.html",
            {"success": "Account created! Please check your email to verify, then login."},
        )

    except Exception as e:
        return templates.TemplateResponse(
            request,
            "signup.html",
            {"error": f"Signup failed: {str(e)}"},
            status_code=400,
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


# ─────── Password reset ───────

@router.get("/forgot-password", response_class=HTMLResponse)
async def forgot_password_page(request: Request):
    return templates.TemplateResponse(request, "forgot_password.html")


@router.post("/forgot-password")
async def forgot_password(request: Request, email: str = Form(...)):
    """Trigger Supabase password-reset email. Always shows success — we don't
    leak whether the email exists (standard security practice)."""
    redirect_to = f"{_app_base_url(request)}/auth/reset-password"
    try:
        supabase.auth.reset_password_for_email(email, {"redirect_to": redirect_to})
    except Exception:
        # Swallow — same response regardless of whether the email exists
        pass
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"sent": True, "email": email},
    )


@router.get("/reset-password", response_class=HTMLResponse)
async def reset_password_page(request: Request):
    """Renders a form. Supabase delivers the recovery token in the URL hash,
    which only JS can read — page submits it back along with the new password."""
    return templates.TemplateResponse(request, "reset_password.html")


@router.post("/reset-password")
async def reset_password(
    request: Request,
    access_token: str = Form(...),
    refresh_token: str = Form(...),
    password: str = Form(...),
):
    """Apply the new password using the recovery-token session."""
    if len(password) < 6:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"error": "Password must be at least 6 characters."},
            status_code=400,
        )
    try:
        supabase.auth.set_session(access_token, refresh_token)
        supabase.auth.update_user({"password": password})
        supabase.auth.sign_out()
    except Exception as exc:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"error": f"Reset failed: {exc}. The link may have expired — request a new one."},
            status_code=400,
        )
    return templates.TemplateResponse(
        request,
        "login.html",
        {"success": "Password updated. Sign in with your new password."},
    )
