import json
import os
import re
import anthropic
from dotenv import load_dotenv

# .env wins over the shell. Some environments (e.g. the Claude desktop app)
# export ANTHROPIC_API_KEY="" which would otherwise mask the real key.
load_dotenv(override=True)

_client = None


def _get_client() -> anthropic.Anthropic:
    """Lazy-init so .env loading happens before the SDK reads the env var."""
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is missing or empty. "
                "Set it in .env (or unset the empty shell override)."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client

_SYSTEM = "You are an expert technical recruiter. Analyze job postings and extract structured information. Return only valid JSON."

_SYSTEM_BLOCK = [{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}]


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    try:
        return json.loads(raw.strip())
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON from model: {e}") from e


def analyze_job(description: str) -> dict:
    if not description:
        return {"summary": "—", "requirements": ""}

    try:
        response = _get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=512,
            system=_SYSTEM_BLOCK,
            messages=[{
                "role": "user",
                "content": (
                    "Analyze this job posting and return ONLY valid JSON:\n"
                    '{"summary": "2-3 sentences: what the company does, the role, YOE if stated",'
                    ' "requirements": ["tool1", "skill2"]}\n\n'
                    "Rules:\n"
                    "- requirements: hard skills and tools only, no soft skills\n"
                    "- requirements: [] if none found\n\n"
                    f"Job posting:\n{description[:3000]}"
                )
            }]
        )
        parsed = _parse_json(response.content[0].text)
    except Exception as exc:
        print(f"[ai_client.analyze_job] {type(exc).__name__}: {exc}")
        return {"summary": "—", "requirements": ""}

    reqs = [r for r in parsed.get("requirements", []) if r]
    return {
        "summary": parsed.get("summary", "—"),
        "requirements": ", ".join(reqs),
    }


def score_job_match(job_description: str, resume_text: str) -> dict:
    if not job_description or not resume_text:
        return {"score": 0, "reasoning": "Insufficient data"}

    try:
        response = _get_client().messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            system=_SYSTEM_BLOCK,
            messages=[{
                "role": "user",
                "content": (
                    "Score how well this candidate matches this job. Return ONLY valid JSON:\n"
                    '{"score": <0-100>, "reasoning": "<one sentence>"}\n\n'
                    f"Resume:\n{resume_text[:2000]}\n\n"
                    f"Job posting:\n{job_description[:2000]}"
                )
            }]
        )
        parsed = _parse_json(response.content[0].text)
    except Exception as exc:
        print(f"[ai_client.score_job_match] {type(exc).__name__}: {exc}")
        return {"score": 0, "reasoning": "Analysis unavailable"}

    return {
        "score": int(parsed.get("score", 0)),
        "reasoning": parsed.get("reasoning", ""),
    }
