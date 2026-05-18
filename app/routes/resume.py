import asyncio
import logging

from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import get_current_user, supabase
from app.utils.resume_parser import parse_resume

router = APIRouter()
logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

_MAX_BYTES = 5 * 1024 * 1024  # 5 MB


@router.get("/", response_class=HTMLResponse)
async def resume_page(request: Request, user=Depends(get_current_user)):
    profile = (
        supabase.table("profiles")
        .select("resume_text, resume_filename")
        .eq("id", user["id"])
        .single()
        .execute()
    )
    data = profile.data or {}
    return templates.TemplateResponse(request, "resume.html", {
        "user": user,
        "has_resume": bool(data.get("resume_text")),
        "resume_filename": data.get("resume_filename"),
        "uploaded": request.query_params.get("uploaded") == "1",
    })


@router.post("/upload")
async def upload_resume(
    request: Request,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
):
    contents = await file.read()
    if len(contents) > _MAX_BYTES:
        raise HTTPException(status_code=400, detail="File too large (max 5 MB)")

    try:
        resume_text = parse_resume(contents, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    supabase.table("profiles").update({
        "resume_text": resume_text,
        "resume_filename": file.filename,
    }).eq("id", user["id"]).execute()

    return RedirectResponse(url="/resume/?uploaded=1", status_code=303)


@router.post("/rescore-all")
async def rescore_all_jobs(
    request: Request,
    user=Depends(get_current_user),
):
    """Re-score all jobs that don't have a match_score yet."""
    from app.utils.ai_client import score_job_match

    profile = supabase.table("profiles").select("resume_text").eq("id", user["id"]).single().execute()
    resume_text = (profile.data or {}).get("resume_text") or ""
    if not resume_text:
        return JSONResponse({"error": "No resume uploaded"}, status_code=400)

    jobs_resp = (
        supabase.table("jobs")
        .select("id, description")
        .eq("user_id", user["id"])
        .is_("match_score", "null")
        .not_.is_("description", "null")
        .execute()
    )
    jobs = jobs_resp.data or []

    scored = 0
    for job in jobs:
        try:
            match = await asyncio.to_thread(score_job_match, job["description"], resume_text)
            supabase.table("jobs").update({
                "match_score": match["score"],
                "match_reasoning": match["reasoning"],
            }).eq("id", job["id"]).execute()
            scored += 1
        except Exception as exc:
            logger.warning("rescore failed for job %s: %s", job["id"], exc)
            continue

    return {"scored": scored, "total": len(jobs)}
