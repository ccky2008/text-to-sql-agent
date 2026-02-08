"""Service for managing SQL pair candidates in MongoDB."""

import logging
from datetime import UTC, datetime
from typing import Any

from text_to_sql.config import get_settings
from text_to_sql.models.training_data import CandidateStatus, compute_question_hash

logger = logging.getLogger(__name__)

COLLECTION_NAME = "sql_pair_candidates"


def _to_object_id(candidate_id: str) -> Any:
    """Convert a string ID to a BSON ObjectId, or return None on failure."""
    from bson import ObjectId

    try:
        return ObjectId(candidate_id)
    except Exception:
        return None


class SQLPairCandidateManager:
    """Manages SQL pair candidates using MongoDB (motor async client).

    Follows the same pattern as SessionManager in checkpointer.py.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._mongodb_uri = settings.mongodb_uri
        self._mongodb_database = settings.mongodb_database
        self._motor_client: Any = None
        self._collection: Any = None
        # In-memory fallback when MongoDB is not configured
        self._memory_store: list[dict[str, Any]] = []
        self._use_memory = settings.session_storage_type != "mongodb"

    async def initialize(self) -> None:
        """Initialize MongoDB connection and create indexes."""
        if self._collection is not None:
            return

        if self._use_memory:
            return

        from motor.motor_asyncio import AsyncIOMotorClient

        self._motor_client = AsyncIOMotorClient(self._mongodb_uri)
        db = self._motor_client[self._mongodb_database]
        self._collection = db[COLLECTION_NAME]
        await self._collection.create_index("question_hash", unique=True)
        await self._collection.create_index("status")
        await self._collection.create_index("created_at")

    async def close(self) -> None:
        """Close the MongoDB connection."""
        if self._motor_client is not None:
            self._motor_client.close()
            self._motor_client = None
        self._collection = None

    def _find_memory_item(self, candidate_id: str) -> dict[str, Any] | None:
        """Find an item in the memory store by ID or question_hash."""
        for item in self._memory_store:
            if item.get("id", item["question_hash"]) == candidate_id:
                return item
        return None

    async def save_candidate(
        self,
        question: str,
        sql_query: str,
        session_id: str | None = None,
    ) -> bool:
        """Save a SQL pair candidate using upsert (dedup by question_hash).

        Returns True if a new candidate was inserted, False if it already existed.
        """
        question_hash = compute_question_hash(question)
        now = datetime.now(UTC)

        if self._collection is not None:
            result = await self._collection.update_one(
                {"question_hash": question_hash},
                {
                    "$setOnInsert": {
                        "question": question,
                        "sql_query": sql_query,
                        "question_hash": question_hash,
                        "status": CandidateStatus.PENDING.value,
                        "session_id": session_id,
                        "created_at": now,
                        "updated_at": now,
                    }
                },
                upsert=True,
            )
            return result.upserted_id is not None

        # Memory fallback
        for item in self._memory_store:
            if item["question_hash"] == question_hash:
                return False
        self._memory_store.append(
            {
                "question": question,
                "sql_query": sql_query,
                "question_hash": question_hash,
                "status": CandidateStatus.PENDING.value,
                "session_id": session_id,
                "created_at": now,
                "updated_at": now,
            }
        )
        return True

    async def list_candidates(
        self,
        status: CandidateStatus | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        """List candidates with optional status filter and pagination.

        Returns (items, total_count).
        """
        query: dict[str, Any] = {}
        if status is not None:
            query["status"] = status.value

        if self._collection is not None:
            total = await self._collection.count_documents(query)
            skip = (page - 1) * page_size
            cursor = (
                self._collection.find(query)
                .sort("created_at", -1)
                .skip(skip)
                .limit(page_size)
            )
            items = []
            async for doc in cursor:
                doc["id"] = str(doc.pop("_id"))
                items.append(doc)
            return items, total

        # Memory fallback
        filtered = [
            item for item in self._memory_store if status is None or item["status"] == status.value
        ]
        filtered.sort(key=lambda x: x["created_at"], reverse=True)
        total = len(filtered)
        start = (page - 1) * page_size
        items = []
        for item in filtered[start : start + page_size]:
            doc = dict(item)
            if "id" not in doc:
                doc["id"] = doc["question_hash"]
            items.append(doc)
        return items, total

    async def get_candidate(self, candidate_id: str) -> dict[str, Any] | None:
        """Get a single candidate by ID."""
        if self._collection is not None:
            oid = _to_object_id(candidate_id)
            if oid is None:
                return None
            doc = await self._collection.find_one({"_id": oid})
            if doc:
                doc["id"] = str(doc.pop("_id"))
                return doc
            return None

        # Memory fallback
        item = self._find_memory_item(candidate_id)
        return dict(item) if item else None

    async def update_candidate_status(
        self, candidate_id: str, status: CandidateStatus
    ) -> bool:
        """Update the status of a candidate."""
        if self._collection is not None:
            oid = _to_object_id(candidate_id)
            if oid is None:
                return False
            result = await self._collection.update_one(
                {"_id": oid},
                {"$set": {"status": status.value, "updated_at": datetime.now(UTC)}},
            )
            return result.modified_count > 0

        # Memory fallback
        item = self._find_memory_item(candidate_id)
        if item is None:
            return False
        item["status"] = status.value
        item["updated_at"] = datetime.now(UTC)
        return True

    async def update_candidate(
        self,
        candidate_id: str,
        question: str | None = None,
        sql_query: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a candidate's question and/or SQL query."""
        update_fields: dict[str, Any] = {"updated_at": datetime.now(UTC)}
        if question is not None:
            update_fields["question"] = question
            update_fields["question_hash"] = compute_question_hash(question)
        if sql_query is not None:
            update_fields["sql_query"] = sql_query

        if self._collection is not None:
            oid = _to_object_id(candidate_id)
            if oid is None:
                return None
            result = await self._collection.find_one_and_update(
                {"_id": oid},
                {"$set": update_fields},
                return_document=True,
            )
            if result:
                result["id"] = str(result.pop("_id"))
                return result
            return None

        # Memory fallback
        item = self._find_memory_item(candidate_id)
        if item is None:
            return None
        item.update(update_fields)
        return dict(item)

    async def delete_candidate(self, candidate_id: str) -> bool:
        """Delete a candidate."""
        if self._collection is not None:
            oid = _to_object_id(candidate_id)
            if oid is None:
                return False
            result = await self._collection.delete_one({"_id": oid})
            return result.deleted_count > 0

        # Memory fallback
        for i, item in enumerate(self._memory_store):
            if item.get("id", item["question_hash"]) == candidate_id:
                self._memory_store.pop(i)
                return True
        return False

    async def get_counts(self) -> dict[str, int]:
        """Get counts of candidates by status."""
        if self._collection is not None:
            pipeline = [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}},
            ]
            counts = {s.value: 0 for s in CandidateStatus}
            async for doc in self._collection.aggregate(pipeline):
                counts[doc["_id"]] = doc["count"]
            total = sum(counts.values())
            return {**counts, "total": total}

        # Memory fallback
        counts = {s.value: 0 for s in CandidateStatus}
        for item in self._memory_store:
            counts[item["status"]] = counts.get(item["status"], 0) + 1
        total = sum(counts.values())
        return {**counts, "total": total}


_candidate_manager: SQLPairCandidateManager | None = None


def get_candidate_manager() -> SQLPairCandidateManager:
    """Get singleton candidate manager instance."""
    global _candidate_manager
    if _candidate_manager is None:
        _candidate_manager = SQLPairCandidateManager()
    return _candidate_manager
