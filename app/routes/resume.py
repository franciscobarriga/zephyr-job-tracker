from fastapi import APIRouter, Request, Depends, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

from app.auth import get_current_user, supabase
from app.utils.resume_parser import parse_resume

router = APIRouter()
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
    return templates.TemplateResponse("resume.html", {
        "request": request,
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

    resume_text = parse_resume(contents, file.filename)

    supabase.table("profiles").update({
        "resume_text": resume_text,
        "resume_filename": file.filename,
    }).eq("id", user["id"]).execute()

    return RedirectResponse(url="/resume/?uploaded=1", status_code=303)
