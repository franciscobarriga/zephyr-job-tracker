import pytest
import os
from unittest.mock import MagicMock, patch


# Patch Supabase env vars and client before app.auth is imported by any test module.
# This prevents the ValueError raised when credentials are missing.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")

with patch("supabase.create_client", return_value=MagicMock()):
    import app.auth  # noqa: F401 — ensure module loads with mocked client


@pytest.fixture
def mock_supabase():
    with patch("app.auth.supabase") as mock:
        yield mock


@pytest.fixture
def mock_current_user():
    return {"id": "test-user-uuid", "email": "test@example.com", "user_metadata": {"username": "testuser"}}
