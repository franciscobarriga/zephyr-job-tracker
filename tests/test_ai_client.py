import json
import pytest
from unittest.mock import MagicMock, patch


def _make_message_response(text: str):
    """Build a minimal mock anthropic Message response."""
    mock_response = MagicMock()
    mock_response.content = [MagicMock(text=text)]
    return mock_response


class TestAnalyzeJob:
    def test_returns_summary_and_requirements(self):
        payload = json.dumps({
            "summary": "A fintech startup building payment APIs. Role focuses on Python backend.",
            "requirements": ["Python", "FastAPI", "PostgreSQL"]
        })
        with patch("app.utils.ai_client._get_client") as mock_client:
            mock_client.return_value.messages.create.return_value = _make_message_response(payload)
            from app.utils.ai_client import analyze_job
            result = analyze_job("some job description")

        assert result["summary"] == "A fintech startup building payment APIs. Role focuses on Python backend."
        assert result["requirements"] == "Python, FastAPI, PostgreSQL"

    def test_handles_empty_description(self):
        from app.utils.ai_client import analyze_job
        result = analyze_job("")
        assert result == {"summary": "—", "requirements": ""}

    def test_strips_markdown_code_block(self):
        payload = "```json\n" + json.dumps({"summary": "A role.", "requirements": ["Go"]}) + "\n```"
        with patch("app.utils.ai_client._get_client") as mock_client:
            mock_client.return_value.messages.create.return_value = _make_message_response(payload)
            from app.utils.ai_client import analyze_job
            result = analyze_job("some job description")

        assert result["requirements"] == "Go"

    def test_returns_empty_requirements_when_none(self):
        payload = json.dumps({"summary": "A role.", "requirements": []})
        with patch("app.utils.ai_client._get_client") as mock_client:
            mock_client.return_value.messages.create.return_value = _make_message_response(payload)
            from app.utils.ai_client import analyze_job
            result = analyze_job("some job")

        assert result["requirements"] == ""


class TestScoreJobMatch:
    def test_returns_score_and_reasoning(self):
        payload = json.dumps({"score": 82, "reasoning": "Strong Python and FastAPI match."})
        with patch("app.utils.ai_client._get_client") as mock_client:
            mock_client.return_value.messages.create.return_value = _make_message_response(payload)
            from app.utils.ai_client import score_job_match
            result = score_job_match("job desc", "resume text")

        assert result["score"] == 82
        assert "Python" in result["reasoning"]

    def test_returns_zero_score_for_empty_inputs(self):
        from app.utils.ai_client import score_job_match
        result = score_job_match("", "")
        assert result["score"] == 0
