"""
LLM client for Zephyr — provider-agnostic.

Selected via the LLM_PROVIDER env var:
  - "gemini"     (default, free tier) — Google Gemini
  - "anthropic"  (paid)                — Claude

Both providers run the same prompts and return the same shape, so callers
(`analyze_job`, `score_job_match`, plus the upcoming tailoring functions)
do not care which is active. Flip LLM_PROVIDER to swap.
"""

import json
import os
import re
from dotenv import load_dotenv

# .env wins over the shell (some envs export ANTHROPIC_API_KEY="" or
# similar empty placeholders that would otherwise mask the real value).
load_dotenv(override=True)

LLM_PROVIDER = (os.environ.get("LLM_PROVIDER") or "gemini").lower()
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-flash-lite-latest")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-4-6")

_SYSTEM = (
    "You are an expert technical recruiter. Analyze job postings and extract "
    "structured information. Return only valid JSON."
)
_SYSTEM_BLOCK = [{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}]


# ─────────────────────── provider clients (lazy) ───────────────────────

_anthropic_client = None
_gemini_client = None


def _get_anthropic():
    global _anthropic_client
    if _anthropic_client is None:
        import anthropic
        key = os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise RuntimeError("ANTHROPIC_API_KEY is missing or empty.")
        _anthropic_client = anthropic.Anthropic(api_key=key)
    return _anthropic_client


def _get_gemini():
    global _gemini_client
    if _gemini_client is None:
        from google import genai
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError("GEMINI_API_KEY is missing or empty.")
        _gemini_client = genai.Client(api_key=key)
    return _gemini_client


# ─────────────────────── unified call ───────────────────────

def _llm_call(prompt: str, max_tokens: int) -> str:
    """Send one prompt to whichever provider is configured. Returns raw text."""
    if LLM_PROVIDER == "gemini":
        client = _get_gemini()
        resp = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{_SYSTEM}\n\n{prompt}",
            config={
                "max_output_tokens": max_tokens,
                "temperature": 0.3,
            },
        )
        return (resp.text or "").strip()

    if LLM_PROVIDER == "anthropic":
        client = _get_anthropic()
        resp = client.messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=max_tokens,
            system=_SYSTEM_BLOCK,
            messages=[{"role": "user", "content": prompt}],
        )
        return resp.content[0].text

    raise RuntimeError(
        f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}. Use 'gemini' or 'anthropic'."
    )


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from model: {e}") from e


# ─────────────────────── public API ───────────────────────

def analyze_job(description: str) -> dict:
    """Return {'summary': str, 'requirements': comma-separated str}."""
    if not description:
        return {"summary": "—", "requirements": ""}

    prompt = (
        "Analyze this job posting and return ONLY valid JSON:\n"
        '{"summary": "2-3 sentences: what the company does, the role, YOE if stated",'
        ' "requirements": ["tool1", "skill2"]}\n\n'
        "Rules:\n"
        "- requirements: hard skills and tools only, no soft skills\n"
        "- requirements: [] if none found\n\n"
        f"Job posting:\n{description[:3000]}"
    )
    try:
        parsed = _parse_json(_llm_call(prompt, max_tokens=512))
    except Exception as exc:
        print(f"[ai_client.analyze_job] {type(exc).__name__}: {exc}")
        return {"summary": "—", "requirements": ""}

    reqs = [r for r in parsed.get("requirements", []) if r]
    return {
        "summary": parsed.get("summary", "—"),
        "requirements": ", ".join(reqs),
    }


def score_job_match(job_description: str, resume_text: str) -> dict:
    """Return {'score': 0..100, 'reasoning': str}."""
    if not job_description or not resume_text:
        return {"score": 0, "reasoning": "Insufficient data"}

    prompt = (
        "Score how well this candidate matches this job. Return ONLY valid JSON:\n"
        '{"score": <0-100>, "reasoning": "<one sentence>"}\n\n'
        f"Resume:\n{resume_text[:2000]}\n\n"
        f"Job posting:\n{job_description[:2000]}"
    )
    try:
        parsed = _parse_json(_llm_call(prompt, max_tokens=256))
    except Exception as exc:
        print(f"[ai_client.score_job_match] {type(exc).__name__}: {exc}")
        return {"score": 0, "reasoning": "Analysis unavailable"}

    return {
        "score": int(parsed.get("score", 0)),
        "reasoning": parsed.get("reasoning", ""),
    }
