"""Tests for SQL generator node."""

from text_to_sql.agents.nodes.sql_generator import _filter_system_columns_from_doc


class TestFilterSystemColumnsFromDoc:
    """Test _filter_system_columns_from_doc function."""

    def test_filters_sys_id(self):
        """Test filtering sysId column."""
        doc = """Table: public.users
Columns:
  - id (integer) PRIMARY KEY
  - sysId (uuid)
  - name (varchar)"""

        result = _filter_system_columns_from_doc(doc)

        assert "id (integer)" in result
        assert "name (varchar)" in result
        assert "sysId" not in result

    def test_filters_all_system_columns(self):
        """Test filtering all system columns."""
        doc = """Table: public.users
Columns:
  - id (integer) PRIMARY KEY
  - sysId (uuid)
  - name (varchar)
  - createdAt (timestamp)
  - updatedAt (timestamp)
  - deletedAt (timestamp)
  - email (varchar)"""

        result = _filter_system_columns_from_doc(doc)

        assert "id (integer)" in result
        assert "name (varchar)" in result
        assert "email (varchar)" in result
        assert "sysId" not in result
        assert "createdAt" not in result
        assert "updatedAt" not in result
        assert "deletedAt" not in result

    def test_preserves_table_info(self):
        """Test that table name and description are preserved."""
        doc = """Table: public.users
Description: User accounts table
Columns:
  - id (integer) PRIMARY KEY
  - sysId (uuid)"""

        result = _filter_system_columns_from_doc(doc)

        assert "Table: public.users" in result
        assert "Description: User accounts table" in result
        assert "Columns:" in result
        assert "id (integer)" in result
        assert "sysId" not in result

    def test_preserves_fk_references(self):
        """Test that FK references are preserved for non-system columns."""
        doc = """Table: public.orders
Columns:
  - user_id (integer) REFERENCES users
  - sysId (uuid)"""

        result = _filter_system_columns_from_doc(doc)

        assert "user_id (integer) REFERENCES users" in result
        assert "sysId" not in result

    def test_preserves_column_descriptions(self):
        """Test that column descriptions are preserved."""
        doc = """Table: public.users
Columns:
  - id (integer) PRIMARY KEY -- User identifier
  - sysId (uuid)
  - email (varchar) -- User email address"""

        result = _filter_system_columns_from_doc(doc)

        assert "id (integer) PRIMARY KEY -- User identifier" in result
        assert "email (varchar) -- User email address" in result
        assert "sysId" not in result

    def test_no_system_columns(self):
        """Test document with no system columns returns unchanged."""
        doc = """Table: public.products
Columns:
  - id (integer) PRIMARY KEY
  - name (varchar)
  - price (decimal)"""

        result = _filter_system_columns_from_doc(doc)

        assert result == doc

    def test_empty_document(self):
        """Test empty document returns empty string."""
        result = _filter_system_columns_from_doc("")
        assert result == ""

    def test_custom_exclusion_set(self):
        """Test filtering with custom exclusion set."""
        doc = """Table: public.users
Columns:
  - id (integer)
  - internal_field (varchar)
  - name (varchar)"""

        result = _filter_system_columns_from_doc(
            doc, excluded=frozenset({"internal_field"})
        )

        assert "id (integer)" in result
        assert "name (varchar)" in result
        assert "internal_field" not in result

    def test_handles_various_data_types(self):
        """Test filtering works with various data type formats."""
        doc = """Table: public.test
Columns:
  - sysId (uuid)
  - createdAt (timestamp with time zone)
  - updatedAt (timestamp without time zone)
  - deletedAt (timestamptz)
  - name (character varying(255))"""

        result = _filter_system_columns_from_doc(doc)

        assert "name (character varying(255))" in result
        assert "sysId" not in result
        assert "createdAt" not in result
        assert "updatedAt" not in result
        assert "deletedAt" not in result

    def test_does_not_filter_similar_column_names(self):
        """Test that columns with similar but different names are not filtered."""
        doc = """Table: public.test
Columns:
  - systemId (varchar)
  - created_at (timestamp)
  - updated_at_utc (timestamp)
  - sysId (uuid)"""

        result = _filter_system_columns_from_doc(doc)

        # These should be kept (different naming convention)
        assert "systemId (varchar)" in result
        assert "created_at (timestamp)" in result
        assert "updated_at_utc (timestamp)" in result
        # This should be filtered (exact match)
        assert "sysId" not in result
