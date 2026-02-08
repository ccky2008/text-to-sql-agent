"""Tests for training data API endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from text_to_sql.api.v1.training_data import router
from text_to_sql.models.training_data import CandidateStatus


def _make_candidate_doc(
    id: str = "abc123",
    question: str = "Show all users",
    sql_query: str = "SELECT * FROM users",
    status: str = "pending",
    session_id: str | None = "session-1",
):
    """Helper to create a candidate document dict."""
    now = datetime.now(UTC)
    return {
        "id": id,
        "question": question,
        "sql_query": sql_query,
        "question_hash": "abcdef1234567890",
        "status": status,
        "session_id": session_id,
        "created_at": now,
        "updated_at": now,
    }


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


@pytest.fixture
def mock_manager():
    """Create mock candidate manager."""
    with patch("text_to_sql.api.v1.training_data.get_candidate_manager") as mock:
        mgr = AsyncMock()
        mock.return_value = mgr
        yield mgr


@pytest.fixture
def mock_vector_store():
    """Create mock vector store service."""
    with patch("text_to_sql.api.v1.training_data.get_vector_store_service") as mock:
        store = MagicMock()
        mock.return_value = store
        yield store


class TestListCandidates:
    """Test list candidates endpoint."""

    def test_list_all(self, client, mock_manager):
        doc = _make_candidate_doc()
        mock_manager.list_candidates.return_value = ([doc], 1)

        response = client.get("/api/v1/training-data/candidates")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["question"] == "Show all users"

    def test_list_with_status_filter(self, client, mock_manager):
        mock_manager.list_candidates.return_value = ([], 0)

        response = client.get("/api/v1/training-data/candidates?status=approved")
        assert response.status_code == 200
        mock_manager.list_candidates.assert_called_once_with(
            status=CandidateStatus.APPROVED, page=1, page_size=20
        )

    def test_list_with_pagination(self, client, mock_manager):
        mock_manager.list_candidates.return_value = ([], 0)

        response = client.get("/api/v1/training-data/candidates?page=2&page_size=10")
        assert response.status_code == 200
        mock_manager.list_candidates.assert_called_once_with(
            status=None, page=2, page_size=10
        )

    def test_list_empty(self, client, mock_manager):
        mock_manager.list_candidates.return_value = ([], 0)

        response = client.get("/api/v1/training-data/candidates")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []


class TestGetCounts:
    """Test counts endpoint."""

    def test_get_counts(self, client, mock_manager):
        mock_manager.get_counts.return_value = {
            "pending": 5,
            "approved": 3,
            "rejected": 2,
            "total": 10,
        }

        response = client.get("/api/v1/training-data/candidates/counts")
        assert response.status_code == 200
        data = response.json()
        assert data["pending"] == 5
        assert data["approved"] == 3
        assert data["rejected"] == 2
        assert data["total"] == 10


class TestGetCandidate:
    """Test get single candidate endpoint."""

    def test_get_existing(self, client, mock_manager):
        doc = _make_candidate_doc(id="test-id")
        mock_manager.get_candidate.return_value = doc

        response = client.get("/api/v1/training-data/candidates/test-id")
        assert response.status_code == 200
        assert response.json()["id"] == "test-id"

    def test_get_not_found(self, client, mock_manager):
        mock_manager.get_candidate.return_value = None

        response = client.get("/api/v1/training-data/candidates/nonexistent")
        assert response.status_code == 404


class TestUpdateCandidate:
    """Test update candidate endpoint."""

    def test_update_question(self, client, mock_manager):
        updated_doc = _make_candidate_doc(question="Updated question")
        mock_manager.update_candidate.return_value = updated_doc

        response = client.put(
            "/api/v1/training-data/candidates/abc123",
            json={"question": "Updated question"},
        )
        assert response.status_code == 200
        assert response.json()["question"] == "Updated question"

    def test_update_not_found(self, client, mock_manager):
        mock_manager.update_candidate.return_value = None

        response = client.put(
            "/api/v1/training-data/candidates/nonexistent",
            json={"question": "Updated"},
        )
        assert response.status_code == 404


class TestApproveCandidate:
    """Test approve candidate endpoint."""

    def test_approve_basic(self, client, mock_manager, mock_vector_store):
        doc = _make_candidate_doc()
        approved_doc = _make_candidate_doc(status="approved")
        mock_manager.get_candidate.side_effect = [doc, approved_doc]
        mock_manager.update_candidate_status.return_value = True

        response = client.post(
            "/api/v1/training-data/candidates/abc123/approve",
            json={},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "approved"
        mock_vector_store.add_sql_pair.assert_called_once()

    def test_approve_with_overrides(self, client, mock_manager, mock_vector_store):
        doc = _make_candidate_doc()
        approved_doc = _make_candidate_doc(
            question="New Q", sql_query="NEW SQL", status="approved"
        )
        # get_candidate called 3 times: initial check, after update, after status change
        mock_manager.get_candidate.side_effect = [doc, approved_doc, approved_doc]
        mock_manager.update_candidate.return_value = approved_doc
        mock_manager.update_candidate_status.return_value = True

        response = client.post(
            "/api/v1/training-data/candidates/abc123/approve",
            json={"question": "New Q", "sql_query": "NEW SQL"},
        )
        assert response.status_code == 200
        mock_manager.update_candidate.assert_called_once()
        mock_vector_store.add_sql_pair.assert_called_once()

    def test_approve_not_found(self, client, mock_manager, mock_vector_store):
        mock_manager.get_candidate.return_value = None

        response = client.post(
            "/api/v1/training-data/candidates/nonexistent/approve",
            json={},
        )
        assert response.status_code == 404


class TestRejectCandidate:
    """Test reject candidate endpoint."""

    def test_reject(self, client, mock_manager):
        rejected_doc = _make_candidate_doc(status="rejected")
        mock_manager.update_candidate_status.return_value = True
        mock_manager.get_candidate.return_value = rejected_doc

        response = client.post("/api/v1/training-data/candidates/abc123/reject")
        assert response.status_code == 200
        assert response.json()["status"] == "rejected"

    def test_reject_not_found(self, client, mock_manager):
        mock_manager.update_candidate_status.return_value = False

        response = client.post("/api/v1/training-data/candidates/nonexistent/reject")
        assert response.status_code == 404


class TestDeleteCandidate:
    """Test delete candidate endpoint."""

    def test_delete(self, client, mock_manager):
        mock_manager.delete_candidate.return_value = True

        response = client.delete("/api/v1/training-data/candidates/abc123")
        assert response.status_code == 200
        assert response.json()["deleted"] is True

    def test_delete_not_found(self, client, mock_manager):
        mock_manager.delete_candidate.return_value = False

        response = client.delete("/api/v1/training-data/candidates/nonexistent")
        assert response.status_code == 404


class TestBulkApprove:
    """Test bulk approve endpoint."""

    def test_bulk_approve(self, client, mock_manager, mock_vector_store):
        doc1 = _make_candidate_doc(id="id1", question="Q1", sql_query="SQL1")
        doc2 = _make_candidate_doc(id="id2", question="Q2", sql_query="SQL2")
        mock_manager.get_candidate.side_effect = [doc1, doc2]
        mock_manager.update_candidate_status.return_value = True

        response = client.post(
            "/api/v1/training-data/candidates/bulk-approve",
            json={"ids": ["id1", "id2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert data["error_count"] == 0
        assert mock_vector_store.add_sql_pair.call_count == 2

    def test_bulk_approve_partial_failure(self, client, mock_manager, mock_vector_store):
        doc1 = _make_candidate_doc(id="id1")
        mock_manager.get_candidate.side_effect = [doc1, None]
        mock_manager.update_candidate_status.return_value = True

        response = client.post(
            "/api/v1/training-data/candidates/bulk-approve",
            json={"ids": ["id1", "id2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 1
        assert data["error_count"] == 1


class TestBulkReject:
    """Test bulk reject endpoint."""

    def test_bulk_reject(self, client, mock_manager):
        mock_manager.update_candidate_status.return_value = True

        response = client.post(
            "/api/v1/training-data/candidates/bulk-reject",
            json={"ids": ["id1", "id2"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 2
        assert data["error_count"] == 0

    def test_bulk_reject_not_found(self, client, mock_manager):
        mock_manager.update_candidate_status.return_value = False

        response = client.post(
            "/api/v1/training-data/candidates/bulk-reject",
            json={"ids": ["nonexistent"]},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success_count"] == 0
        assert data["error_count"] == 1
