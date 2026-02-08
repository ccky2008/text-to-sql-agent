"""Tests for SQLPairCandidateManager (memory mode)."""

import pytest

from text_to_sql.models.training_data import CandidateStatus, compute_question_hash
from text_to_sql.services.sql_pair_candidates import SQLPairCandidateManager


@pytest.fixture
def manager():
    """Create a SQLPairCandidateManager in memory mode for testing."""
    mgr = SQLPairCandidateManager.__new__(SQLPairCandidateManager)
    mgr._mongodb_uri = ""
    mgr._mongodb_database = ""
    mgr._motor_client = None
    mgr._collection = None
    mgr._memory_store = []
    mgr._use_memory = True
    return mgr


class TestComputeQuestionHash:
    """Test the question hash function."""

    def test_basic_hash(self):
        h = compute_question_hash("Show all users")
        assert len(h) == 16
        assert isinstance(h, str)

    def test_case_insensitive(self):
        h1 = compute_question_hash("Show all users")
        h2 = compute_question_hash("SHOW ALL USERS")
        assert h1 == h2

    def test_strips_whitespace(self):
        h1 = compute_question_hash("Show all users")
        h2 = compute_question_hash("  Show all users  ")
        assert h1 == h2

    def test_different_questions_different_hashes(self):
        h1 = compute_question_hash("Show all users")
        h2 = compute_question_hash("Count all orders")
        assert h1 != h2


class TestSaveCandidate:
    """Test saving candidates."""

    async def test_save_new_candidate(self, manager):
        result = await manager.save_candidate(
            question="Show all users",
            sql_query="SELECT * FROM users",
            session_id="session-1",
        )
        assert result is True
        assert len(manager._memory_store) == 1
        assert manager._memory_store[0]["question"] == "Show all users"
        assert manager._memory_store[0]["sql_query"] == "SELECT * FROM users"
        assert manager._memory_store[0]["status"] == "pending"
        assert manager._memory_store[0]["session_id"] == "session-1"

    async def test_save_duplicate_returns_false(self, manager):
        await manager.save_candidate(
            question="Show all users", sql_query="SELECT * FROM users"
        )
        result = await manager.save_candidate(
            question="Show all users", sql_query="SELECT id FROM users"
        )
        assert result is False
        assert len(manager._memory_store) == 1
        # Original SQL should remain unchanged
        assert manager._memory_store[0]["sql_query"] == "SELECT * FROM users"

    async def test_dedup_case_insensitive(self, manager):
        await manager.save_candidate(
            question="Show all users", sql_query="SELECT * FROM users"
        )
        result = await manager.save_candidate(
            question="SHOW ALL USERS", sql_query="SELECT * FROM users"
        )
        assert result is False
        assert len(manager._memory_store) == 1

    async def test_save_without_session_id(self, manager):
        result = await manager.save_candidate(
            question="Count orders", sql_query="SELECT COUNT(*) FROM orders"
        )
        assert result is True
        assert manager._memory_store[0]["session_id"] is None


class TestListCandidates:
    """Test listing candidates."""

    async def test_list_empty(self, manager):
        items, total = await manager.list_candidates()
        assert items == []
        assert total == 0

    async def test_list_all(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        await manager.save_candidate("Q2", "SQL2")
        items, total = await manager.list_candidates()
        assert total == 2
        assert len(items) == 2

    async def test_list_filter_by_status(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        await manager.save_candidate("Q2", "SQL2")
        # Manually change status of one
        manager._memory_store[0]["status"] = "approved"

        items, total = await manager.list_candidates(status=CandidateStatus.PENDING)
        assert total == 1
        assert items[0]["question"] == "Q2"

        items, total = await manager.list_candidates(status=CandidateStatus.APPROVED)
        assert total == 1
        assert items[0]["question"] == "Q1"

    async def test_list_pagination(self, manager):
        for i in range(5):
            await manager.save_candidate(f"Q{i}", f"SQL{i}")

        items, total = await manager.list_candidates(page=1, page_size=2)
        assert total == 5
        assert len(items) == 2

        items, total = await manager.list_candidates(page=3, page_size=2)
        assert total == 5
        assert len(items) == 1


class TestGetCandidate:
    """Test getting a single candidate."""

    async def test_get_existing(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        candidate_id = manager._memory_store[0].get(
            "id", manager._memory_store[0]["question_hash"]
        )
        doc = await manager.get_candidate(candidate_id)
        assert doc is not None
        assert doc["question"] == "Q1"

    async def test_get_nonexistent(self, manager):
        doc = await manager.get_candidate("nonexistent")
        assert doc is None


class TestUpdateCandidateStatus:
    """Test status updates."""

    async def test_update_to_approved(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        candidate_id = manager._memory_store[0].get(
            "id", manager._memory_store[0]["question_hash"]
        )
        result = await manager.update_candidate_status(
            candidate_id, CandidateStatus.APPROVED
        )
        assert result is True
        assert manager._memory_store[0]["status"] == "approved"

    async def test_update_to_rejected(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        candidate_id = manager._memory_store[0].get(
            "id", manager._memory_store[0]["question_hash"]
        )
        result = await manager.update_candidate_status(
            candidate_id, CandidateStatus.REJECTED
        )
        assert result is True
        assert manager._memory_store[0]["status"] == "rejected"

    async def test_update_nonexistent(self, manager):
        result = await manager.update_candidate_status(
            "nonexistent", CandidateStatus.APPROVED
        )
        assert result is False


class TestUpdateCandidate:
    """Test editing candidates."""

    async def test_update_question(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        candidate_id = manager._memory_store[0].get(
            "id", manager._memory_store[0]["question_hash"]
        )
        doc = await manager.update_candidate(candidate_id, question="New Q")
        assert doc is not None
        assert doc["question"] == "New Q"

    async def test_update_sql(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        candidate_id = manager._memory_store[0].get(
            "id", manager._memory_store[0]["question_hash"]
        )
        doc = await manager.update_candidate(candidate_id, sql_query="NEW SQL")
        assert doc is not None
        assert doc["sql_query"] == "NEW SQL"

    async def test_update_nonexistent(self, manager):
        doc = await manager.update_candidate("nonexistent", question="New Q")
        assert doc is None


class TestDeleteCandidate:
    """Test deleting candidates."""

    async def test_delete_existing(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        candidate_id = manager._memory_store[0].get(
            "id", manager._memory_store[0]["question_hash"]
        )
        result = await manager.delete_candidate(candidate_id)
        assert result is True
        assert len(manager._memory_store) == 0

    async def test_delete_nonexistent(self, manager):
        result = await manager.delete_candidate("nonexistent")
        assert result is False


class TestGetCounts:
    """Test count aggregation."""

    async def test_empty_counts(self, manager):
        counts = await manager.get_counts()
        assert counts["pending"] == 0
        assert counts["approved"] == 0
        assert counts["rejected"] == 0
        assert counts["total"] == 0

    async def test_mixed_counts(self, manager):
        await manager.save_candidate("Q1", "SQL1")
        await manager.save_candidate("Q2", "SQL2")
        await manager.save_candidate("Q3", "SQL3")
        manager._memory_store[0]["status"] = "approved"
        manager._memory_store[1]["status"] = "rejected"

        counts = await manager.get_counts()
        assert counts["pending"] == 1
        assert counts["approved"] == 1
        assert counts["rejected"] == 1
        assert counts["total"] == 3
