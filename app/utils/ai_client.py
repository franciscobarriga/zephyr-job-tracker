import json
import re
import anthropic

_client = anthropic.Anthropic()

_SYSTEM = "You are an expert technical recruiter. Analyze job postings and extract structured information. Return only valid JSON."

_SYSTEM_BLOCK = [{"type": "text", "text": _SYSTEM, "cache_control": {"type": "ephemeral"}}]


def _parse_json(raw: str) -> dict:
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```(?:json)?\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
    return json.loads(raw.strip())


def analyze_job(description: str) -> dict:
    if not description:
        return {"summary": "—", "requirements": ""}

    response = _client.messages.create(
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
    reqs = [r for r in parsed.get("requirements", []) if r]
    return {
        "summary": parsed.get("summary", "—"),
        "requirements": ", ".join(reqs),
    }


def score_job_match(job_description: str, resume_text: str) -> dict:
    if not job_description or not resume_text:
        return {"score": 0, "reasoning": "Insufficient data"}

    response = _client.messages.create(
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
    return {
        "score": int(parsed.get("score", 0)),
        "reasoning": parsed.get("reasoning", ""),
    }
