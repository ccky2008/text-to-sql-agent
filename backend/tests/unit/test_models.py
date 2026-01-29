"""Tests for data models."""

from text_to_sql.core.types import MetadataCategory
from text_to_sql.models.data_sources import ColumnInfo, MetadataEntry, SQLPair, TableInfo


class TestSQLPair:
    """Test SQLPair model."""

    def test_create_sql_pair(self):
        """Test creating a SQL pair."""
        pair = SQLPair(
            question="Show all users",
            sql_query="SELECT * FROM users",
        )

        assert pair.question == "Show all users"
        assert pair.sql_query == "SELECT * FROM users"
        assert pair.id is not None

    def test_to_embedding_text(self):
        """Test embedding text generation."""
        pair = SQLPair(
            question="Count active users",
            sql_query="SELECT COUNT(*) FROM users WHERE active = true",
        )

        text = pair.to_embedding_text()

        assert "Count active users" in text
        assert "SELECT COUNT(*)" in text

    def test_to_metadata(self):
        """Test metadata conversion."""
        pair = SQLPair(
            question="Test question",
            sql_query="SELECT 1",
        )

        meta = pair.to_metadata()

        assert meta["question"] == "Test question"
        assert meta["sql_query"] == "SELECT 1"
        assert "id" in meta


class TestMetadataEntry:
    """Test MetadataEntry model."""

    def test_create_metadata_entry(self):
        """Test creating a metadata entry."""
        entry = MetadataEntry(
            title="Active User",
            content="A user who has logged in within the last 30 days",
            category=MetadataCategory.DOMAIN_TERM,
            related_tables=["users", "sessions"],
            keywords=["active", "login", "user"],
        )

        assert entry.title == "Active User"
        assert entry.category == MetadataCategory.DOMAIN_TERM
        assert "users" in entry.related_tables

    def test_to_embedding_text(self):
        """Test embedding text generation."""
        entry = MetadataEntry(
            title="Revenue Calculation",
            content="Revenue is calculated as sum of completed order amounts",
            category=MetadataCategory.BUSINESS_RULE,
            keywords=["revenue", "orders"],
        )

        text = entry.to_embedding_text()

        assert "Revenue Calculation" in text
        assert "sum of completed order amounts" in text
        assert "revenue" in text


class TestTableInfo:
    """Test TableInfo model."""

    def test_create_table_info(self):
        """Test creating table info."""
        columns = [
            ColumnInfo(name="id", data_type="integer", is_primary_key=True),
            ColumnInfo(name="name", data_type="varchar(255)"),
            ColumnInfo(name="email", data_type="varchar(255)", is_nullable=False),
        ]

        table = TableInfo(
            schema_name="public",
            table_name="users",
            columns=columns,
            description="Stores user information",
        )

        assert table.full_name == "public.users"
        assert len(table.columns) == 3
        assert table.columns[0].is_primary_key

    def test_to_ddl(self):
        """Test DDL generation."""
        columns = [
            ColumnInfo(name="id", data_type="integer", is_primary_key=True, is_nullable=False),
            ColumnInfo(name="name", data_type="varchar(255)"),
        ]

        table = TableInfo(
            table_name="test_table",
            columns=columns,
        )

        ddl = table.to_ddl()

        assert "CREATE TABLE" in ddl
        assert "test_table" in ddl
        assert "PRIMARY KEY" in ddl
        assert "NOT NULL" in ddl

    def test_to_embedding_text(self):
        """Test embedding text generation."""
        columns = [
            ColumnInfo(
                name="user_id",
                data_type="integer",
                is_foreign_key=True,
                foreign_key_table="users",
            ),
        ]

        table = TableInfo(
            table_name="orders",
            columns=columns,
            description="Customer orders",
        )

        text = table.to_embedding_text()

        assert "orders" in text
        assert "Customer orders" in text
        assert "user_id" in text
        assert "REFERENCES users" in text

    def test_get_visible_columns_filters_system_columns(self):
        """Test that get_visible_columns filters out system columns."""
        columns = [
            ColumnInfo(name="id", data_type="integer", is_primary_key=True),
            ColumnInfo(name="name", data_type="varchar(255)"),
            ColumnInfo(name="sysId", data_type="uuid"),
            ColumnInfo(name="createdAt", data_type="timestamp"),
            ColumnInfo(name="updatedAt", data_type="timestamp"),
            ColumnInfo(name="deletedAt", data_type="timestamp"),
        ]

        table = TableInfo(table_name="users", columns=columns)
        visible = table.get_visible_columns()

        assert len(visible) == 2
        visible_names = [c.name for c in visible]
        assert "id" in visible_names
        assert "name" in visible_names
        assert "sysId" not in visible_names
        assert "createdAt" not in visible_names
        assert "updatedAt" not in visible_names
        assert "deletedAt" not in visible_names

    def test_get_visible_columns_with_custom_exclusions(self):
        """Test get_visible_columns with custom exclusion set."""
        columns = [
            ColumnInfo(name="id", data_type="integer"),
            ColumnInfo(name="secret", data_type="varchar"),
            ColumnInfo(name="name", data_type="varchar"),
        ]

        table = TableInfo(table_name="users", columns=columns)
        visible = table.get_visible_columns(excluded=frozenset({"secret"}))

        assert len(visible) == 2
        visible_names = [c.name for c in visible]
        assert "id" in visible_names
        assert "name" in visible_names
        assert "secret" not in visible_names

    def test_get_visible_columns_no_system_columns(self):
        """Test get_visible_columns when table has no system columns."""
        columns = [
            ColumnInfo(name="id", data_type="integer"),
            ColumnInfo(name="name", data_type="varchar"),
        ]

        table = TableInfo(table_name="simple_table", columns=columns)
        visible = table.get_visible_columns()

        assert len(visible) == 2

    def test_to_embedding_text_filtered(self):
        """Test to_embedding_text_filtered excludes system columns."""
        columns = [
            ColumnInfo(name="id", data_type="integer", is_primary_key=True),
            ColumnInfo(name="email", data_type="varchar"),
            ColumnInfo(name="sysId", data_type="uuid"),
            ColumnInfo(name="createdAt", data_type="timestamp"),
        ]

        table = TableInfo(
            table_name="users",
            columns=columns,
            description="User accounts",
        )

        text = table.to_embedding_text_filtered()

        assert "users" in text
        assert "User accounts" in text
        assert "id" in text
        assert "email" in text
        assert "sysId" not in text
        assert "createdAt" not in text

    def test_to_embedding_text_filtered_preserves_metadata(self):
        """Test to_embedding_text_filtered preserves FK and PK info."""
        columns = [
            ColumnInfo(
                name="user_id",
                data_type="integer",
                is_foreign_key=True,
                foreign_key_table="users",
                description="The user who owns this",
            ),
            ColumnInfo(name="sysId", data_type="uuid"),
        ]

        table = TableInfo(table_name="orders", columns=columns)
        text = table.to_embedding_text_filtered()

        assert "user_id" in text
        assert "REFERENCES users" in text
        assert "The user who owns this" in text
        assert "sysId" not in text
