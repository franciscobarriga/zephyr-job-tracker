"""
Authentication utilities and Supabase client
"""

from fastapi import Request, HTTPException, status
from supabase import create_client, Client
import os

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")

if not SUPABASE_URL or not SUPABASE_ANON_KEY:
    raise ValueError("Missing Supabase credentials in environment")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)


async def get_current_user(request: Request):
    """
    Dependency to get current authenticated user from session
    Raises HTTPException if not authenticated
    """
    user = request.session.get("user")
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return user


async def get_current_user_optional(request: Request):
    """Get current user if logged in, else None"""
    return request.session.get("user")
