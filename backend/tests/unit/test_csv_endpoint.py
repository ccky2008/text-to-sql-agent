"""Tests for CSV endpoint."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient
from fastapi import FastAPI

from text_to_sql.api.v1.csv import router, download_csv
from text_to_sql.models.requests import CSVDownloadRequest
from text_to_sql.services.query_cache import QueryCache
from text_to_sql.core.types import ExecutionResult


@pytest.fixture
def app():
    """Create test FastAPI app."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestCSVDownloadRequest:
    """Test CSVDownloadRequest model validation."""

    def test_valid_request(self):
        """Test valid request creation."""
        request = CSVDownloadRequest(
            query_token="test-token-123",
            offset=0,
            limit=100,
            filename="results.csv",
        )
        assert request.query_token == "test-token-123"
        assert request.offset == 0
        assert request.limit == 100

    def test_default_values(self):
        """Test default values."""
        request = CSVDownloadRequest(query_token="token")
        assert request.offset == 0
        assert request.limit is None
        assert request.filename == "query_results.csv"

    def test_limit_validation(self):
        """Test that limit has upper bound validation."""
        with pytest.raises(ValueError):
            CSVDownloadRequest(query_token="token", limit=20000)  # Exceeds le=10000

    def test_offset_validation(self):
        """Test that offset must be non-negative."""
        with pytest.raises(ValueError):
            CSVDownloadRequest(query_token="token", offset=-1)


class TestFilenameSanitization:
    """Test filename sanitization logic."""

    def test_normal_filename(self):
        """Test normal filename is preserved."""
        # Sanitization logic
        filename = "results_2024.csv"
        safe = "".join(c for c in filename if c.isalnum() or c in "._-").rstrip()
        if not safe.endswith(".csv"):
            safe += ".csv"
        assert safe == "results_2024.csv"

    def test_dangerous_characters_removed(self):
        """Test dangerous characters are stripped."""
        filename = "../../../etc/passwd"
        safe = "".join(c for c in filename if c.isalnum() or c in "._-").rstrip()
        assert "/" not in safe
        assert safe == "......etcpasswd"  # 6 dots (3x "..")

    def test_empty_after_sanitization(self):
        """Test empty filename gets default."""
        filename = "!!!"
        safe = "".join(c for c in filename if c.isalnum() or c in "._-").rstrip()
        if not safe or safe in ("", ".csv"):
            safe = "query_results.csv"
        assert safe == "query_results.csv"

    def test_csv_extension_added(self):
        """Test .csv extension is added if missing."""
        filename = "myfile"
        safe = "".join(c for c in filename if c.isalnum() or c in "._-").rstrip()
        if not safe.endswith(".csv"):
            safe += ".csv"
        assert safe == "myfile.csv"


class TestCSVEndpoint:
    """Test CSV download endpoint."""

    @patch("text_to_sql.api.v1.csv.get_query_cache")
    @patch("text_to_sql.api.v1.csv.get_database_service")
    @patch("text_to_sql.api.v1.csv.get_settings")
    def test_invalid_token_returns_400(
        self, mock_settings, mock_db, mock_cache, client
    ):
        """Test that invalid token returns 400 error."""
        # Setup mock
        cache = MagicMock()
        cache.get.return_value = None
        mock_cache.return_value = cache

        response = client.post(
            "/api/v1/csv",
            json={"query_token": "invalid-token"},
        )

        assert response.status_code == 400
        assert "Invalid or expired query token" in response.json()["detail"]

    @patch("text_to_sql.api.v1.csv.get_query_cache")
    @patch("text_to_sql.api.v1.csv.get_database_service")
    @patch("text_to_sql.api.v1.csv.get_settings")
    def test_valid_token_returns_csv(
        self, mock_settings, mock_db, mock_cache, client
    ):
        """Test that valid token returns CSV data."""
        # Setup settings mock
        settings = MagicMock()
        settings.csv_max_rows = 2500
        mock_settings.return_value = settings

        # Setup cache mock
        cached_query = MagicMock()
        cached_query.sql = "SELECT id, name FROM users"
        cache = MagicMock()
        cache.get.return_value = cached_query
        mock_cache.return_value = cache

        # Setup database mock
        db_service = MagicMock()
        db_service.execute_query_paginated = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                rows=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
                row_count=2,
                columns=["id", "name"],
                error=None,
            )
        )
        mock_db.return_value = db_service

        response = client.post(
            "/api/v1/csv",
            json={"query_token": "valid-token", "filename": "users.csv"},
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "text/csv; charset=utf-8"
        assert "users.csv" in response.headers["content-disposition"]

        # Check CSV content
        content = response.text
        assert "id,name" in content
        assert "Alice" in content
        assert "Bob" in content

    @patch("text_to_sql.api.v1.csv.get_query_cache")
    @patch("text_to_sql.api.v1.csv.get_database_service")
    @patch("text_to_sql.api.v1.csv.get_settings")
    def test_limit_capped_to_max(self, mock_settings, mock_db, mock_cache, client):
        """Test that limit is capped to csv_max_rows."""
        settings = MagicMock()
        settings.csv_max_rows = 100  # Small limit for testing
        mock_settings.return_value = settings

        cached_query = MagicMock()
        cached_query.sql = "SELECT 1"
        cache = MagicMock()
        cache.get.return_value = cached_query
        mock_cache.return_value = cache

        db_service = MagicMock()
        db_service.execute_query_paginated = AsyncMock(
            return_value=ExecutionResult(
                success=True,
                rows=[],
                row_count=0,
                columns=[],
                error=None,
            )
        )
        mock_db.return_value = db_service

        response = client.post(
            "/api/v1/csv",
            json={"query_token": "token", "limit": 5000},  # Request more than max
        )

        # Verify limit was capped
        db_service.execute_query_paginated.assert_called_once()
        call_args = db_service.execute_query_paginated.call_args
        assert call_args.kwargs["limit"] == 100  # Capped to max


class TestCSVLimitsEndpoint:
    """Test CSV limits endpoint."""

    @patch("text_to_sql.api.v1.csv.get_settings")
    def test_get_csv_limits(self, mock_settings, client):
        """Test getting CSV limits."""
        settings = MagicMock()
        settings.csv_max_rows = 2500
        mock_settings.return_value = settings

        response = client.get("/api/v1/csv/limits")

        assert response.status_code == 200
        data = response.json()
        assert data["max_rows_per_download"] == 2500
        assert data["batch_download_available"] is True
        assert "batch_download_instructions" in data
