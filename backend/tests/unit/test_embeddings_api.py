"""Tests for embeddings API endpoints."""

import json
import pytest
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from text_to_sql.api.v1.embeddings import router
from text_to_sql.models.data_sources import ColumnInfo, MetadataEntry, SQLPair, TableInfo
from text_to_sql.core.types import MetadataCategory


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
def mock_vector_store():
    """Create mock vector store service."""
    with patch("text_to_sql.api.v1.embeddings.get_vector_store_service") as mock:
        store = MagicMock()
        mock.return_value = store
        yield store


class TestSQLPairsEndpoints:
    """Test SQL pairs CRUD endpoints."""

    def test_list_sql_pairs(self, client, mock_vector_store):
        """Test listing SQL pairs with pagination."""
        mock_vector_store.list_sql_pairs.return_value = [
            {
                "id": "pair-1",
                "metadata": {
                    "id": "pair-1",
                    "question": "Show all users",
                    "sql_query": "SELECT * FROM users",
                },
            },
            {
                "id": "pair-2",
                "metadata": {
                    "id": "pair-2",
                    "question": "Count orders",
                    "sql_query": "SELECT COUNT(*) FROM orders",
                },
            },
        ]
        mock_vector_store.get_sql_pairs_count.return_value = 2

        response = client.get("/api/v1/embeddings/sql-pairs?page=1&page_size=20")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["question"] == "Show all users"

    def test_list_sql_pairs_empty(self, client, mock_vector_store):
        """Test listing SQL pairs when empty."""
        mock_vector_store.list_sql_pairs.return_value = []
        mock_vector_store.get_sql_pairs_count.return_value = 0

        response = client.get("/api/v1/embeddings/sql-pairs")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert data["items"] == []

    def test_create_sql_pair(self, client, mock_vector_store):
        """Test creating a SQL pair."""
        mock_vector_store.add_sql_pair.return_value = ("new-pair-id", False)

        response = client.post(
            "/api/v1/embeddings/sql-pairs",
            json={
                "question": "Show all products",
                "sql_query": "SELECT * FROM products",
                "description": "List all products",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["question"] == "Show all products"
        assert data["sql_query"] == "SELECT * FROM products"
        mock_vector_store.add_sql_pair.assert_called_once()

    def test_get_sql_pair(self, client, mock_vector_store):
        """Test getting a single SQL pair."""
        mock_vector_store.get_sql_pair.return_value = {
            "id": "pair-1",
            "metadata": {
                "id": "pair-1",
                "question": "Test question",
                "sql_query": "SELECT 1",
            },
        }

        response = client.get("/api/v1/embeddings/sql-pairs/pair-1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "pair-1"
        assert data["question"] == "Test question"

    def test_get_sql_pair_not_found(self, client, mock_vector_store):
        """Test getting a non-existent SQL pair."""
        mock_vector_store.get_sql_pair.return_value = None

        response = client.get("/api/v1/embeddings/sql-pairs/not-found")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"]

    def test_update_sql_pair(self, client, mock_vector_store):
        """Test updating a SQL pair."""
        mock_vector_store.update_sql_pair.return_value = {
            "id": "pair-1",
            "metadata": {
                "id": "pair-1",
                "question": "Updated question",
                "sql_query": "SELECT 1",
            },
        }

        response = client.put(
            "/api/v1/embeddings/sql-pairs/pair-1",
            json={"question": "Updated question"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["question"] == "Updated question"

    def test_update_sql_pair_not_found(self, client, mock_vector_store):
        """Test updating a non-existent SQL pair."""
        mock_vector_store.update_sql_pair.return_value = None

        response = client.put(
            "/api/v1/embeddings/sql-pairs/not-found",
            json={"question": "Updated"},
        )

        assert response.status_code == 404

    def test_delete_sql_pair(self, client, mock_vector_store):
        """Test deleting a SQL pair."""
        mock_vector_store.delete_sql_pair.return_value = True

        response = client.delete("/api/v1/embeddings/sql-pairs/pair-1")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_sql_pair_not_found(self, client, mock_vector_store):
        """Test deleting a non-existent SQL pair."""
        mock_vector_store.delete_sql_pair.return_value = False

        response = client.delete("/api/v1/embeddings/sql-pairs/not-found")

        assert response.status_code == 404

    def test_bulk_create_sql_pairs(self, client, mock_vector_store):
        """Test bulk creating SQL pairs."""
        mock_vector_store.add_sql_pair.side_effect = [
            ("id-1", False),  # New
            ("id-2", True),   # Updated
        ]

        response = client.post(
            "/api/v1/embeddings/sql-pairs/bulk",
            json=[
                {"question": "Q1", "sql_query": "SELECT 1"},
                {"question": "Q2", "sql_query": "SELECT 2"},
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1
        assert data["updated"] == 1
        assert data["failed"] == 0

    def test_bulk_delete_sql_pairs(self, client, mock_vector_store):
        """Test bulk deleting SQL pairs."""
        mock_vector_store.delete_sql_pairs_bulk.return_value = (2, ["not-found"])

        response = client.request(
            "DELETE",
            "/api/v1/embeddings/sql-pairs/bulk/delete",
            json={"ids": ["id-1", "id-2", "not-found"]},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["deleted"] == 2
        assert data["not_found"] == ["not-found"]


class TestMetadataEndpoints:
    """Test metadata CRUD endpoints."""

    def test_list_metadata(self, client, mock_vector_store):
        """Test listing metadata entries."""
        mock_vector_store.list_metadata.return_value = [
            {
                "id": "meta-1",
                "metadata": {
                    "id": "meta-1",
                    "title": "Active User",
                    "content": "A user who logged in recently",
                    "category": "domain_term",
                    "related_tables": "users,sessions",
                    "keywords": "active,user",
                },
            },
        ]
        mock_vector_store.get_metadata_count.return_value = 1

        response = client.get("/api/v1/embeddings/metadata")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["title"] == "Active User"
        assert data["items"][0]["related_tables"] == ["users", "sessions"]

    def test_create_metadata(self, client, mock_vector_store):
        """Test creating a metadata entry."""
        mock_vector_store.add_metadata.return_value = ("meta-id", False)

        response = client.post(
            "/api/v1/embeddings/metadata",
            json={
                "title": "Revenue Definition",
                "content": "Total sales minus returns",
                "category": "business_rule",
                "related_tables": ["orders", "returns"],
                "keywords": ["revenue", "sales"],
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "Revenue Definition"
        assert data["category"] == "business_rule"

    def test_get_metadata(self, client, mock_vector_store):
        """Test getting a single metadata entry."""
        mock_vector_store.get_metadata_entry.return_value = {
            "id": "meta-1",
            "metadata": {
                "id": "meta-1",
                "title": "Test",
                "content": "Content",
                "category": "domain_term",
                "related_tables": "",
                "keywords": "",
            },
        }

        response = client.get("/api/v1/embeddings/metadata/meta-1")

        assert response.status_code == 200
        assert response.json()["title"] == "Test"

    def test_get_metadata_not_found(self, client, mock_vector_store):
        """Test getting a non-existent metadata entry."""
        mock_vector_store.get_metadata_entry.return_value = None

        response = client.get("/api/v1/embeddings/metadata/not-found")

        assert response.status_code == 404

    def test_update_metadata(self, client, mock_vector_store):
        """Test updating a metadata entry."""
        mock_vector_store.update_metadata.return_value = {
            "id": "meta-1",
            "metadata": {
                "id": "meta-1",
                "title": "New Title",
                "content": "Old content",
                "category": "domain_term",
                "related_tables": "",
                "keywords": "",
            },
        }

        response = client.put(
            "/api/v1/embeddings/metadata/meta-1",
            json={"title": "New Title"},
        )

        assert response.status_code == 200
        assert response.json()["title"] == "New Title"

    def test_update_metadata_not_found(self, client, mock_vector_store):
        """Test updating a non-existent metadata entry."""
        mock_vector_store.update_metadata.return_value = None

        response = client.put(
            "/api/v1/embeddings/metadata/not-found",
            json={"title": "New Title"},
        )

        assert response.status_code == 404

    def test_delete_metadata(self, client, mock_vector_store):
        """Test deleting a metadata entry."""
        mock_vector_store.delete_metadata.return_value = True

        response = client.delete("/api/v1/embeddings/metadata/meta-1")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_metadata_not_found(self, client, mock_vector_store):
        """Test deleting a non-existent metadata entry."""
        mock_vector_store.delete_metadata.return_value = False

        response = client.delete("/api/v1/embeddings/metadata/not-found")

        assert response.status_code == 404

    def test_bulk_create_metadata(self, client, mock_vector_store):
        """Test bulk creating metadata entries."""
        mock_vector_store.add_metadata.side_effect = [
            ("id-1", False),
            ("id-2", False),
        ]

        response = client.post(
            "/api/v1/embeddings/metadata/bulk",
            json=[
                {
                    "title": "Term 1",
                    "content": "Content 1",
                    "category": "domain_term",
                },
                {
                    "title": "Term 2",
                    "content": "Content 2",
                    "category": "business_rule",
                },
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2

    def test_bulk_delete_metadata(self, client, mock_vector_store):
        """Test bulk deleting metadata entries."""
        mock_vector_store.delete_metadata_bulk.return_value = (1, [])

        response = client.request(
            "DELETE",
            "/api/v1/embeddings/metadata/bulk/delete",
            json={"ids": ["meta-1"]},
        )

        assert response.status_code == 200
        assert response.json()["deleted"] == 1


class TestDatabaseInfoEndpoints:
    """Test database info CRUD endpoints."""

    def test_list_database_info(self, client, mock_vector_store):
        """Test listing database info."""
        mock_vector_store.list_database_info.return_value = [
            {
                "id": "table-1",
                "metadata": {
                    "id": "table-1",
                    "schema_name": "public",
                    "table_name": "users",
                    "full_name": "public.users",
                    "description": "User accounts",
                    "column_count": 3,
                    "columns_json": json.dumps([
                        {"name": "id", "data_type": "integer", "is_primary_key": True},
                        {"name": "name", "data_type": "varchar"},
                        {"name": "email", "data_type": "varchar"},
                    ]),
                    "relationships_json": json.dumps([]),
                },
            },
        ]
        mock_vector_store.get_database_info_count.return_value = 1

        response = client.get("/api/v1/embeddings/database-info")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["table_name"] == "users"
        assert len(data["items"][0]["columns"]) == 3

    def test_create_database_info(self, client, mock_vector_store):
        """Test creating database info."""
        mock_vector_store.add_table_info.return_value = ("table-id", False)

        response = client.post(
            "/api/v1/embeddings/database-info",
            json={
                "schema_name": "public",
                "table_name": "products",
                "columns": [
                    {"name": "id", "data_type": "integer", "is_primary_key": True},
                    {"name": "name", "data_type": "varchar"},
                ],
                "description": "Product catalog",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["table_name"] == "products"
        assert len(data["columns"]) == 2

    def test_get_database_info(self, client, mock_vector_store):
        """Test getting a single database info entry."""
        mock_vector_store.get_table_info.return_value = {
            "id": "table-1",
            "metadata": {
                "id": "table-1",
                "schema_name": "public",
                "table_name": "users",
                "full_name": "public.users",
                "description": "",
                "column_count": 1,
                "columns_json": json.dumps([{"name": "id", "data_type": "integer"}]),
                "relationships_json": json.dumps([]),
            },
        }

        response = client.get("/api/v1/embeddings/database-info/table-1")

        assert response.status_code == 200
        assert response.json()["table_name"] == "users"

    def test_get_database_info_not_found(self, client, mock_vector_store):
        """Test getting a non-existent database info entry."""
        mock_vector_store.get_table_info.return_value = None

        response = client.get("/api/v1/embeddings/database-info/not-found")

        assert response.status_code == 404

    def test_update_database_info(self, client, mock_vector_store):
        """Test updating database info."""
        mock_vector_store.update_table_info.return_value = {
            "id": "table-1",
            "metadata": {
                "id": "table-1",
                "schema_name": "public",
                "table_name": "users",
                "full_name": "public.users",
                "description": "User table with accounts",
                "column_count": 1,
                "columns_json": json.dumps([{"name": "id", "data_type": "integer"}]),
                "relationships_json": json.dumps([]),
            },
        }

        response = client.put(
            "/api/v1/embeddings/database-info/table-1",
            json={"description": "User table with accounts"},
        )

        assert response.status_code == 200
        assert response.json()["description"] == "User table with accounts"

    def test_update_database_info_not_found(self, client, mock_vector_store):
        """Test updating a non-existent database info entry."""
        mock_vector_store.update_table_info.return_value = None

        response = client.put(
            "/api/v1/embeddings/database-info/not-found",
            json={"description": "New description"},
        )

        assert response.status_code == 404

    def test_delete_database_info(self, client, mock_vector_store):
        """Test deleting database info."""
        mock_vector_store.delete_table_info.return_value = True

        response = client.delete("/api/v1/embeddings/database-info/table-1")

        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_delete_database_info_not_found(self, client, mock_vector_store):
        """Test deleting a non-existent database info entry."""
        mock_vector_store.delete_table_info.return_value = False

        response = client.delete("/api/v1/embeddings/database-info/not-found")

        assert response.status_code == 404

    def test_bulk_create_database_info(self, client, mock_vector_store):
        """Test bulk creating database info."""
        mock_vector_store.add_table_info.side_effect = [
            ("id-1", False),
            ("id-2", True),
        ]

        response = client.post(
            "/api/v1/embeddings/database-info/bulk",
            json=[
                {
                    "schema_name": "public",
                    "table_name": "table1",
                    "columns": [{"name": "id", "data_type": "integer"}],
                },
                {
                    "schema_name": "public",
                    "table_name": "table2",
                    "columns": [{"name": "id", "data_type": "integer"}],
                },
            ],
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1
        assert data["updated"] == 1

    def test_bulk_delete_database_info(self, client, mock_vector_store):
        """Test bulk deleting database info."""
        mock_vector_store.delete_table_info_bulk.return_value = (2, [])

        response = client.request(
            "DELETE",
            "/api/v1/embeddings/database-info/bulk/delete",
            json={"ids": ["id-1", "id-2"]},
        )

        assert response.status_code == 200
        assert response.json()["deleted"] == 2


class TestDDLImportEndpoint:
    """Test DDL import endpoint."""

    def test_import_ddl_single_table(self, client, mock_vector_store):
        """Test importing DDL with a single table."""
        mock_vector_store.add_table_info.return_value = ("table-id", False)

        ddl = """
        CREATE TABLE users (
            id integer PRIMARY KEY,
            name varchar(255) NOT NULL,
            email varchar(255)
        )
        """

        response = client.post(
            "/api/v1/embeddings/database-info/import-ddl",
            json={"ddl": ddl, "schema_name": "public"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tables_imported"] == 1
        assert len(data["tables"]) == 1
        assert "public.users" in data["tables"]

    def test_import_ddl_multiple_tables(self, client, mock_vector_store):
        """Test importing DDL with multiple tables."""
        mock_vector_store.add_table_info.side_effect = [
            ("id-1", False),
            ("id-2", True),
        ]

        ddl = """
        CREATE TABLE users (id integer PRIMARY KEY);
        CREATE TABLE orders (id integer PRIMARY KEY, user_id integer REFERENCES users(id));
        """

        response = client.post(
            "/api/v1/embeddings/database-info/import-ddl",
            json={"ddl": ddl},
        )

        assert response.status_code == 200
        data = response.json()
        # tables_imported counts all (both new and updated)
        assert data["tables_imported"] == 2
        assert len(data["tables"]) == 2

    def test_import_ddl_empty(self, client, mock_vector_store):
        """Test importing empty DDL."""
        response = client.post(
            "/api/v1/embeddings/database-info/import-ddl",
            json={"ddl": ""},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tables_imported"] == 0
        assert data["tables"] == []

    def test_import_ddl_no_tables(self, client, mock_vector_store):
        """Test importing DDL with no CREATE TABLE statements."""
        ddl = "CREATE INDEX idx_users_email ON users(email);"

        response = client.post(
            "/api/v1/embeddings/database-info/import-ddl",
            json={"ddl": ddl},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tables_imported"] == 0

    def test_import_ddl_with_custom_schema(self, client, mock_vector_store):
        """Test importing DDL with custom schema name."""
        mock_vector_store.add_table_info.return_value = ("table-id", False)

        ddl = "CREATE TABLE products (id integer PRIMARY KEY);"

        response = client.post(
            "/api/v1/embeddings/database-info/import-ddl",
            json={"ddl": ddl, "schema_name": "inventory"},
        )

        assert response.status_code == 200
        # Verify the table info was created with the correct schema
        call_args = mock_vector_store.add_table_info.call_args
        table_info = call_args[0][0]
        assert table_info.schema_name == "inventory"

    def test_import_ddl_typeorm_format(self, client, mock_vector_store):
        """Test importing TypeORM-generated DDL."""
        mock_vector_store.add_table_info.return_value = ("table-id", False)

        ddl = """
        CREATE TABLE "rel_type" (
            "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
            "rel_type" character varying(255) NOT NULL,
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            CONSTRAINT "PK_rel_type" PRIMARY KEY ("id")
        )
        """

        response = client.post(
            "/api/v1/embeddings/database-info/import-ddl",
            json={"ddl": ddl},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["tables_imported"] == 1
        assert "public.rel_type" in data["tables"]

        # Verify the table was created correctly
        call_args = mock_vector_store.add_table_info.call_args
        table_info = call_args[0][0]
        assert table_info.table_name == "rel_type"

        # Find the id column and check its properties
        id_col = next(c for c in table_info.columns if c.name == "id")
        assert id_col.is_primary_key
        assert id_col.data_type == "uuid"


class TestPaginationValidation:
    """Test pagination parameter validation."""

    def test_invalid_page_number(self, client, mock_vector_store):
        """Test that page number must be positive."""
        response = client.get("/api/v1/embeddings/sql-pairs?page=0")
        assert response.status_code == 422

    def test_invalid_page_size(self, client, mock_vector_store):
        """Test that page size must be positive."""
        response = client.get("/api/v1/embeddings/sql-pairs?page_size=0")
        assert response.status_code == 422

    def test_page_size_max_limit(self, client, mock_vector_store):
        """Test that page size has a maximum limit."""
        response = client.get("/api/v1/embeddings/sql-pairs?page_size=1000")
        assert response.status_code == 422


class TestErrorHandling:
    """Test error handling in endpoints."""

    def test_invalid_json_body(self, client, mock_vector_store):
        """Test handling of invalid JSON body."""
        response = client.post(
            "/api/v1/embeddings/sql-pairs",
            content="not valid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422

    def test_missing_required_field(self, client, mock_vector_store):
        """Test handling of missing required fields."""
        response = client.post(
            "/api/v1/embeddings/sql-pairs",
            json={"question": "Only question, no SQL"},
        )
        assert response.status_code == 422

    def test_invalid_metadata_category(self, client, mock_vector_store):
        """Test handling of invalid metadata category."""
        response = client.post(
            "/api/v1/embeddings/metadata",
            json={
                "title": "Test",
                "content": "Content",
                "category": "invalid_category",
            },
        )
        assert response.status_code == 422
