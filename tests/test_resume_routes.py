import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import io


def _make_app_with_mocked_user(mock_user):
    """Create test app that injects a fake current user."""
    from app.main import app
    from app import auth

    async def override_get_current_user():
        return mock_user

    app.dependency_overrides[auth.get_current_user] = override_get_current_user
    return TestClient(app)


class TestResumeGet:
    def test_redirects_unauthenticated_user(self):
        from app.main import app
        client = TestClient(app, follow_redirects=False)
        resp = client.get("/resume/")
        assert resp.status_code in (302, 307)

    def test_shows_upload_form_when_no_resume(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        mock_profile_resp = MagicMock()
        mock_profile_resp.data = {"resume_text": None, "resume_filename": None}

        with patch("app.routes.resume.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile_resp
            client = _make_app_with_mocked_user(mock_user)
            resp = client.get("/resume/")

        assert resp.status_code == 200
        assert "Upload" in resp.text


class TestResumeUpload:
    def test_upload_pdf_updates_profile(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        fake_pdf_bytes = b"%PDF-1.4 fake content"

        with patch("app.routes.resume.parse_resume", return_value="John Doe\nEngineer") as mock_parse, \
             patch("app.routes.resume.supabase") as mock_sb:

            mock_sb.table.return_value.update.return_value.eq.return_value.execute.return_value = MagicMock()
            client = _make_app_with_mocked_user(mock_user)
            resp = client.post(
                "/resume/upload",
                files={"file": ("resume.pdf", io.BytesIO(fake_pdf_bytes), "application/pdf")},
                follow_redirects=False,
            )

        mock_parse.assert_called_once_with(fake_pdf_bytes, "resume.pdf")
        assert resp.status_code in (302, 303)

    def test_rejects_oversized_file(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        big_bytes = b"x" * (6 * 1024 * 1024)  # 6MB

        with patch("app.routes.resume.supabase"):
            client = _make_app_with_mocked_user(mock_user)
            resp = client.post(
                "/resume/upload",
                files={"file": ("big.pdf", io.BytesIO(big_bytes), "application/pdf")},
            )

        assert resp.status_code == 400

    def test_rejects_unparseable_file(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        with patch("app.routes.resume.parse_resume", side_effect=ValueError("Unsupported file type: photo.png")):
            with patch("app.routes.resume.supabase"):
                client = _make_app_with_mocked_user(mock_user)
                resp = client.post(
                    "/resume/upload",
                    files={"file": ("photo.png", io.BytesIO(b"fake"), "image/png")},
                )
        assert resp.status_code == 400
        assert "Unsupported file type" in resp.text


class TestRescoreAll:
    def test_returns_400_when_no_resume(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        mock_profile = MagicMock()
        mock_profile.data = {"resume_text": None}

        with patch("app.routes.resume.supabase") as mock_sb:
            mock_sb.table.return_value.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile
            client = _make_app_with_mocked_user(mock_user)
            resp = client.post("/resume/rescore-all")

        assert resp.status_code == 400
        assert "No resume" in resp.json()["error"]

    def test_scores_unscored_jobs_and_returns_count(self):
        mock_user = {"id": "uid", "email": "a@b.com", "user_metadata": {}}
        mock_profile = MagicMock()
        mock_profile.data = {"resume_text": "Experienced Python engineer"}
        mock_jobs = MagicMock()
        mock_jobs.data = [
            {"id": 1, "description": "Python backend role"},
            {"id": 2, "description": "Java developer role"},
        ]
        mock_update_chain = MagicMock()

        with patch("app.routes.resume.supabase") as mock_sb, \
             patch("app.routes.resume.asyncio.to_thread", return_value={"score": 75, "reasoning": "Good match"}):
            table_mock = mock_sb.table.return_value
            # profile select
            table_mock.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_profile
            # jobs select chain: .select().eq().is_().not_.is_().execute()
            jobs_chain = table_mock.select.return_value.eq.return_value.is_.return_value.not_.is_.return_value
            jobs_chain.execute.return_value = mock_jobs
            # update chain
            table_mock.update.return_value.eq.return_value.execute.return_value = mock_update_chain

            client = _make_app_with_mocked_user(mock_user)
            resp = client.post("/resume/rescore-all")

        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert body["scored"] == 2
