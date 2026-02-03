"""ChromaDB vector store service."""

from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings

from text_to_sql.config import get_settings
from text_to_sql.core.exceptions import VectorStoreError
from text_to_sql.models.data_sources import MetadataEntry, SQLPair, TableInfo
from text_to_sql.services.embedding import get_embedding_service

# Collection names
SQL_PAIRS_COLLECTION = "sql_pairs"
METADATA_COLLECTION = "domain_metadata"
DATABASE_INFO_COLLECTION = "database_info"


class VectorStoreService:
    """Service for vector store operations using ChromaDB."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = chromadb.PersistentClient(
            path=settings.chromadb_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._embedding_service = get_embedding_service()
        self._init_collections()

    def _init_collections(self) -> None:
        """Initialize ChromaDB collections."""
        self._sql_pairs = self._client.get_or_create_collection(
            name=SQL_PAIRS_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._metadata = self._client.get_or_create_collection(
            name=METADATA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._database_info = self._client.get_or_create_collection(
            name=DATABASE_INFO_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    # SQL Pairs operations
    def add_sql_pair(self, pair: SQLPair) -> tuple[str, bool]:
        """Add or update a SQL pair in the vector store.

        Returns:
            Tuple of (pair_id, is_update) where is_update is True if the pair existed.
        """
        try:
            is_update = self.sql_pair_exists(pair.id)
            embedding = self._embedding_service.embed_text(pair.to_embedding_text())
            self._sql_pairs.upsert(
                ids=[pair.id],
                embeddings=[embedding],
                documents=[pair.to_embedding_text()],
                metadatas=[pair.to_metadata()],
            )
            return pair.id, is_update
        except Exception as e:
            raise VectorStoreError(f"Failed to add SQL pair: {e}") from e

    def sql_pair_exists(self, pair_id: str) -> bool:
        """Check if a SQL pair exists in the vector store."""
        try:
            result = self._sql_pairs.get(ids=[pair_id])
            return len(result["ids"]) > 0
        except Exception:
            return False

    def search_sql_pairs(
        self, query: str, n_results: int = 5
    ) -> list[dict[str, Any]]:
        """Search for similar SQL pairs."""
        try:
            embedding = self._embedding_service.embed_text(query)
            results = self._sql_pairs.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            return self._format_results(results)
        except Exception as e:
            raise VectorStoreError(f"Failed to search SQL pairs: {e}") from e

    def list_sql_pairs(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List all SQL pairs."""
        try:
            results = self._sql_pairs.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"],
            )
            return self._format_get_results(results)
        except Exception as e:
            raise VectorStoreError(f"Failed to list SQL pairs: {e}") from e

    def get_sql_pair(self, pair_id: str) -> dict[str, Any] | None:
        """Get a single SQL pair by ID."""
        try:
            result = self._sql_pairs.get(
                ids=[pair_id],
                include=["documents", "metadatas"],
            )
            if not result["ids"]:
                return None
            return {
                "id": result["ids"][0],
                "document": result["documents"][0] if result.get("documents") else None,
                "metadata": result["metadatas"][0] if result.get("metadatas") else {},
            }
        except Exception as e:
            raise VectorStoreError(f"Failed to get SQL pair: {e}") from e

    def update_sql_pair(
        self, pair_id: str, question: str | None = None, sql_query: str | None = None
    ) -> dict[str, Any] | None:
        """Update a SQL pair. Returns updated pair or None if not found."""
        try:
            existing = self.get_sql_pair(pair_id)
            if not existing:
                return None

            current_meta = existing["metadata"]
            new_question = question if question is not None else current_meta.get("question", "")
            new_sql = sql_query if sql_query is not None else current_meta.get("sql_query", "")

            pair = SQLPair(id=pair_id, question=new_question, sql_query=new_sql)
            embedding = self._embedding_service.embed_text(pair.to_embedding_text())

            self._sql_pairs.update(
                ids=[pair_id],
                embeddings=[embedding],
                documents=[pair.to_embedding_text()],
                metadatas=[pair.to_metadata()],
            )

            return {
                "id": pair_id,
                "metadata": pair.to_metadata(),
            }
        except Exception as e:
            raise VectorStoreError(f"Failed to update SQL pair: {e}") from e

    def delete_sql_pair(self, pair_id: str) -> bool:
        """Delete a SQL pair. Returns True if deleted, False if not found."""
        try:
            if not self.sql_pair_exists(pair_id):
                return False
            self._sql_pairs.delete(ids=[pair_id])
            return True
        except Exception as e:
            raise VectorStoreError(f"Failed to delete SQL pair: {e}") from e

    def delete_sql_pairs_bulk(self, pair_ids: list[str]) -> tuple[int, list[str]]:
        """Delete multiple SQL pairs. Returns (deleted_count, not_found_ids)."""
        try:
            not_found = []
            to_delete = []
            for pair_id in pair_ids:
                if self.sql_pair_exists(pair_id):
                    to_delete.append(pair_id)
                else:
                    not_found.append(pair_id)

            if to_delete:
                self._sql_pairs.delete(ids=to_delete)

            return len(to_delete), not_found
        except Exception as e:
            raise VectorStoreError(f"Failed to bulk delete SQL pairs: {e}") from e

    def get_sql_pairs_count(self) -> int:
        """Get total count of SQL pairs."""
        return self._sql_pairs.count()

    # Metadata operations
    def add_metadata(self, entry: MetadataEntry) -> tuple[str, bool]:
        """Add or update a metadata entry in the vector store.

        Returns:
            Tuple of (entry_id, is_update) where is_update is True if the entry existed.
        """
        try:
            is_update = self.metadata_exists(entry.id)
            embedding = self._embedding_service.embed_text(entry.to_embedding_text())
            self._metadata.upsert(
                ids=[entry.id],
                embeddings=[embedding],
                documents=[entry.to_embedding_text()],
                metadatas=[entry.to_metadata()],
            )
            return entry.id, is_update
        except Exception as e:
            raise VectorStoreError(f"Failed to add metadata: {e}") from e

    def metadata_exists(self, entry_id: str) -> bool:
        """Check if a metadata entry exists in the vector store."""
        try:
            result = self._metadata.get(ids=[entry_id])
            return len(result["ids"]) > 0
        except Exception:
            return False

    def search_metadata(
        self, query: str, n_results: int = 5, category: str | None = None
    ) -> list[dict[str, Any]]:
        """Search for similar metadata entries."""
        try:
            embedding = self._embedding_service.embed_text(query)
            where_filter = {"category": category} if category else None
            results = self._metadata.query(
                query_embeddings=[embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )
            return self._format_results(results)
        except Exception as e:
            raise VectorStoreError(f"Failed to search metadata: {e}") from e

    def list_metadata(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List all metadata entries."""
        try:
            results = self._metadata.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"],
            )
            return self._format_get_results(results)
        except Exception as e:
            raise VectorStoreError(f"Failed to list metadata: {e}") from e

    def get_metadata_entry(self, entry_id: str) -> dict[str, Any] | None:
        """Get a single metadata entry by ID."""
        try:
            result = self._metadata.get(
                ids=[entry_id],
                include=["documents", "metadatas"],
            )
            if not result["ids"]:
                return None
            return {
                "id": result["ids"][0],
                "document": result["documents"][0] if result.get("documents") else None,
                "metadata": result["metadatas"][0] if result.get("metadatas") else {},
            }
        except Exception as e:
            raise VectorStoreError(f"Failed to get metadata entry: {e}") from e

    def update_metadata(
        self,
        entry_id: str,
        title: str | None = None,
        content: str | None = None,
        category: str | None = None,
        related_tables: list[str] | None = None,
        keywords: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Update a metadata entry. Returns updated entry or None if not found."""
        from text_to_sql.core.types import MetadataCategory

        try:
            existing = self.get_metadata_entry(entry_id)
            if not existing:
                return None

            current_meta = existing["metadata"]

            new_title = title if title is not None else current_meta.get("title", "")
            new_content = content if content is not None else current_meta.get("content", "")
            cat_str = category if category is not None else current_meta.get("category", "context")
            new_category = MetadataCategory(cat_str)

            current_tables = current_meta.get("related_tables", "")
            if related_tables is not None:
                new_related_tables = related_tables
            else:
                new_related_tables = current_tables.split(",") if current_tables else []

            current_keywords = current_meta.get("keywords", "")
            if keywords is not None:
                new_keywords = keywords
            else:
                new_keywords = current_keywords.split(",") if current_keywords else []

            entry = MetadataEntry(
                id=entry_id,
                title=new_title,
                content=new_content,
                category=new_category,
                related_tables=new_related_tables,
                keywords=new_keywords,
            )
            embedding = self._embedding_service.embed_text(entry.to_embedding_text())

            self._metadata.update(
                ids=[entry_id],
                embeddings=[embedding],
                documents=[entry.to_embedding_text()],
                metadatas=[entry.to_metadata()],
            )

            return {
                "id": entry_id,
                "metadata": entry.to_metadata(),
            }
        except Exception as e:
            raise VectorStoreError(f"Failed to update metadata: {e}") from e

    def delete_metadata(self, entry_id: str) -> bool:
        """Delete a metadata entry. Returns True if deleted, False if not found."""
        try:
            if not self.metadata_exists(entry_id):
                return False
            self._metadata.delete(ids=[entry_id])
            return True
        except Exception as e:
            raise VectorStoreError(f"Failed to delete metadata: {e}") from e

    def delete_metadata_bulk(self, entry_ids: list[str]) -> tuple[int, list[str]]:
        """Delete multiple metadata entries. Returns (deleted_count, not_found_ids)."""
        try:
            not_found = []
            to_delete = []
            for entry_id in entry_ids:
                if self.metadata_exists(entry_id):
                    to_delete.append(entry_id)
                else:
                    not_found.append(entry_id)

            if to_delete:
                self._metadata.delete(ids=to_delete)

            return len(to_delete), not_found
        except Exception as e:
            raise VectorStoreError(f"Failed to bulk delete metadata: {e}") from e

    def get_metadata_count(self) -> int:
        """Get total count of metadata entries."""
        return self._metadata.count()

    # Database Info operations
    def add_table_info(self, table: TableInfo) -> tuple[str, bool]:
        """Add or update table info in the vector store.

        Returns:
            Tuple of (table_id, is_update) where is_update is True if the table existed.
        """
        try:
            is_update = self.table_exists(table.id)
            embedding = self._embedding_service.embed_text(table.to_embedding_text())
            self._database_info.upsert(
                ids=[table.id],
                embeddings=[embedding],
                documents=[table.to_embedding_text()],
                metadatas=[table.to_metadata()],
            )
            return table.id, is_update
        except Exception as e:
            raise VectorStoreError(f"Failed to add table info: {e}") from e

    def table_exists(self, table_id: str) -> bool:
        """Check if a table exists in the vector store."""
        try:
            result = self._database_info.get(ids=[table_id])
            return len(result["ids"]) > 0
        except Exception:
            return False

    def search_database_info(
        self, query: str, n_results: int = 10
    ) -> list[dict[str, Any]]:
        """Search for relevant database schema information."""
        try:
            embedding = self._embedding_service.embed_text(query)
            results = self._database_info.query(
                query_embeddings=[embedding],
                n_results=n_results,
                include=["documents", "metadatas", "distances"],
            )
            return self._format_results(results)
        except Exception as e:
            raise VectorStoreError(f"Failed to search database info: {e}") from e

    def list_database_info(self, limit: int = 100, offset: int = 0) -> list[dict[str, Any]]:
        """List all table info entries."""
        try:
            results = self._database_info.get(
                limit=limit,
                offset=offset,
                include=["documents", "metadatas"],
            )
            return self._format_get_results(results)
        except Exception as e:
            raise VectorStoreError(f"Failed to list database info: {e}") from e

    def get_table_info(self, table_id: str) -> dict[str, Any] | None:
        """Get a single table info by ID."""
        try:
            result = self._database_info.get(
                ids=[table_id],
                include=["documents", "metadatas"],
            )
            if not result["ids"]:
                return None
            return {
                "id": result["ids"][0],
                "document": result["documents"][0] if result.get("documents") else None,
                "metadata": result["metadatas"][0] if result.get("metadatas") else {},
            }
        except Exception as e:
            raise VectorStoreError(f"Failed to get table info: {e}") from e

    def update_table_info(
        self,
        table_id: str,
        schema_name: str | None = None,
        table_name: str | None = None,
        columns: list[dict] | None = None,
        relationships: list[dict] | None = None,
        description: str | None = None,
        row_count: int | None = None,
    ) -> dict[str, Any] | None:
        """Update table info. Returns updated info or None if not found."""
        from text_to_sql.models.data_sources import ColumnInfo, Relationship

        try:
            existing = self.get_table_info(table_id)
            if not existing:
                return None

            current_meta = existing["metadata"]

            new_schema = schema_name if schema_name is not None else current_meta.get("schema_name", "public")
            new_table_name = table_name if table_name is not None else current_meta.get("table_name", "")

            if columns is not None:
                new_columns = [ColumnInfo(**col) for col in columns]
            else:
                new_columns = []

            if relationships is not None:
                new_relationships = [Relationship(**rel) for rel in relationships]
            else:
                new_relationships = []

            new_description = description if description is not None else current_meta.get("description")
            new_row_count = row_count if row_count is not None else current_meta.get("row_count")

            table = TableInfo(
                id=table_id,
                schema_name=new_schema,
                table_name=new_table_name,
                columns=new_columns,
                relationships=new_relationships,
                description=new_description if new_description else None,
                row_count=new_row_count if isinstance(new_row_count, int) else None,
            )
            embedding = self._embedding_service.embed_text(table.to_embedding_text())

            self._database_info.update(
                ids=[table_id],
                embeddings=[embedding],
                documents=[table.to_embedding_text()],
                metadatas=[table.to_metadata()],
            )

            return {
                "id": table_id,
                "metadata": table.to_metadata(),
            }
        except Exception as e:
            raise VectorStoreError(f"Failed to update table info: {e}") from e

    def delete_table_info(self, table_id: str) -> bool:
        """Delete table info. Returns True if deleted, False if not found."""
        try:
            if not self.table_exists(table_id):
                return False
            self._database_info.delete(ids=[table_id])
            return True
        except Exception as e:
            raise VectorStoreError(f"Failed to delete table info: {e}") from e

    def delete_table_info_bulk(self, table_ids: list[str]) -> tuple[int, list[str]]:
        """Delete multiple table info entries. Returns (deleted_count, not_found_ids)."""
        try:
            not_found = []
            to_delete = []
            for table_id in table_ids:
                if self.table_exists(table_id):
                    to_delete.append(table_id)
                else:
                    not_found.append(table_id)

            if to_delete:
                self._database_info.delete(ids=to_delete)

            return len(to_delete), not_found
        except Exception as e:
            raise VectorStoreError(f"Failed to bulk delete table info: {e}") from e

    def get_database_info_count(self) -> int:
        """Get total count of table info entries."""
        return self._database_info.count()

    def clear_collection(self, collection_name: str) -> None:
        """Clear all entries from a collection."""
        try:
            self._client.delete_collection(collection_name)
            self._init_collections()
        except Exception as e:
            raise VectorStoreError(f"Failed to clear collection: {e}") from e

    @staticmethod
    def _format_results(results: dict) -> list[dict[str, Any]]:
        """Format ChromaDB query results."""
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                item = {
                    "id": doc_id,
                    "document": results["documents"][0][i] if results["documents"] else None,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                }
                formatted.append(item)
        return formatted

    @staticmethod
    def _format_get_results(results: dict) -> list[dict[str, Any]]:
        """Format ChromaDB get results."""
        formatted = []
        if results["ids"]:
            for i, doc_id in enumerate(results["ids"]):
                item = {
                    "id": doc_id,
                    "document": results["documents"][i] if results.get("documents") else None,
                    "metadata": results["metadatas"][i] if results.get("metadatas") else {},
                }
                formatted.append(item)
        return formatted


_vector_store_service: VectorStoreService | None = None


def get_vector_store_service() -> VectorStoreService:
    """Get singleton vector store service instance."""
    global _vector_store_service
    if _vector_store_service is None:
        _vector_store_service = VectorStoreService()
    return _vector_store_service
