"""Tests for DDL parser utility."""

import pytest

from text_to_sql.utils.ddl_parser import (
    ParsedColumn,
    ParsedForeignKey,
    ParsedTable,
    parse_ddl,
)


class TestParseDDL:
    """Test parse_ddl function."""

    def test_parse_simple_table(self):
        """Test parsing a simple CREATE TABLE statement."""
        ddl = """
        CREATE TABLE users (
            id integer PRIMARY KEY,
            name varchar(255) NOT NULL,
            email varchar(255)
        )
        """
        tables = parse_ddl(ddl)

        assert len(tables) == 1
        table = tables[0]
        assert table.table_name == "users"
        assert table.schema_name == "public"
        assert len(table.columns) == 3

    def test_parse_quoted_identifiers(self):
        """Test parsing with quoted identifiers."""
        ddl = """
        CREATE TABLE "public"."users" (
            "id" integer PRIMARY KEY,
            "name" varchar(255)
        )
        """
        tables = parse_ddl(ddl)

        assert len(tables) == 1
        table = tables[0]
        assert table.schema_name == "public"
        assert table.table_name == "users"
        assert table.columns[0].name == "id"

    def test_parse_if_not_exists(self):
        """Test parsing with IF NOT EXISTS clause."""
        ddl = """
        CREATE TABLE IF NOT EXISTS products (
            id integer PRIMARY KEY
        )
        """
        tables = parse_ddl(ddl)

        assert len(tables) == 1
        assert tables[0].table_name == "products"

    def test_parse_primary_key_constraint(self):
        """Test parsing table-level PRIMARY KEY constraint."""
        ddl = """
        CREATE TABLE orders (
            id uuid,
            order_number varchar(50),
            CONSTRAINT "PK_orders" PRIMARY KEY ("id")
        )
        """
        tables = parse_ddl(ddl)

        assert len(tables) == 1
        table = tables[0]
        assert "id" in table.primary_key_columns
        # Column should be marked as primary key
        id_col = next(c for c in table.columns if c.name == "id")
        assert id_col.is_primary_key

    def test_parse_foreign_key_inline(self):
        """Test parsing inline REFERENCES clause."""
        ddl = """
        CREATE TABLE orders (
            id integer PRIMARY KEY,
            user_id integer REFERENCES users(id)
        )
        """
        tables = parse_ddl(ddl)

        assert len(tables) == 1
        user_id_col = next(c for c in tables[0].columns if c.name == "user_id")
        assert user_id_col.is_foreign_key
        assert user_id_col.foreign_key_table == "users"
        assert user_id_col.foreign_key_column == "id"

    def test_parse_foreign_key_constraint(self):
        """Test parsing table-level FOREIGN KEY constraint."""
        ddl = """
        CREATE TABLE orders (
            id integer PRIMARY KEY,
            user_id integer,
            CONSTRAINT "FK_orders_users" FOREIGN KEY ("user_id") REFERENCES "users" ("id")
        )
        """
        tables = parse_ddl(ddl)

        assert len(tables) == 1
        table = tables[0]
        assert len(table.foreign_keys) == 1
        fk = table.foreign_keys[0]
        assert fk.from_column == "user_id"
        assert fk.to_table == "users"
        assert fk.to_column == "id"
        # Column should be marked as FK
        user_id_col = next(c for c in table.columns if c.name == "user_id")
        assert user_id_col.is_foreign_key

    def test_parse_not_null(self):
        """Test parsing NOT NULL constraint."""
        ddl = """
        CREATE TABLE users (
            id integer NOT NULL,
            name varchar(255)
        )
        """
        tables = parse_ddl(ddl)

        id_col = next(c for c in tables[0].columns if c.name == "id")
        name_col = next(c for c in tables[0].columns if c.name == "name")
        assert not id_col.is_nullable
        assert name_col.is_nullable

    def test_parse_default_value(self):
        """Test parsing DEFAULT values."""
        ddl = """
        CREATE TABLE users (
            id uuid DEFAULT uuid_generate_v4(),
            created_at timestamp DEFAULT now(),
            status varchar DEFAULT 'active'
        )
        """
        tables = parse_ddl(ddl)

        id_col = next(c for c in tables[0].columns if c.name == "id")
        created_col = next(c for c in tables[0].columns if c.name == "created_at")
        status_col = next(c for c in tables[0].columns if c.name == "status")

        assert id_col.default_value == "uuid_generate_v4()"
        assert created_col.default_value == "now()"
        assert status_col.default_value == "'active'"

    def test_parse_multiple_tables(self):
        """Test parsing multiple CREATE TABLE statements."""
        ddl = """
        CREATE TABLE users (
            id integer PRIMARY KEY
        );

        CREATE TABLE orders (
            id integer PRIMARY KEY,
            user_id integer REFERENCES users(id)
        );
        """
        tables = parse_ddl(ddl)

        assert len(tables) == 2
        assert tables[0].table_name == "users"
        assert tables[1].table_name == "orders"

    def test_parse_complex_data_types(self):
        """Test parsing complex PostgreSQL data types."""
        ddl = """
        CREATE TABLE events (
            id integer,
            created_at TIMESTAMP WITH TIME ZONE,
            updated_at TIMESTAMP WITHOUT TIME ZONE,
            price DOUBLE PRECISION,
            description CHARACTER VARYING(1000)
        )
        """
        tables = parse_ddl(ddl)

        cols = {c.name: c for c in tables[0].columns}
        assert cols["created_at"].data_type == "timestamp with time zone"
        assert cols["updated_at"].data_type == "timestamp without time zone"
        assert cols["price"].data_type == "double precision"
        assert "character varying" in cols["description"].data_type

    def test_parse_typeorm_ddl(self):
        """Test parsing TypeORM-generated DDL."""
        ddl = """
        CREATE TABLE "rel_type" (
            "id" uuid NOT NULL DEFAULT uuid_generate_v4(),
            "rel_type" character varying(255) NOT NULL,
            "displayName" character varying(255) NOT NULL,
            "sysId" uuid DEFAULT uuid_generate_v4(),
            "createdAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "updatedAt" TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
            "deletedAt" TIMESTAMP WITH TIME ZONE,
            CONSTRAINT "PK_rel_type" PRIMARY KEY ("id"),
            CONSTRAINT "UQ_rel_type_rel_type" UNIQUE ("rel_type")
        )
        """
        tables = parse_ddl(ddl)

        assert len(tables) == 1
        table = tables[0]
        assert table.table_name == "rel_type"
        assert "id" in table.primary_key_columns

        cols = {c.name: c for c in table.columns}
        assert cols["id"].is_primary_key
        assert cols["id"].default_value == "uuid_generate_v4()"
        assert not cols["id"].is_nullable
        assert cols["createdAt"].data_type == "timestamp with time zone"
        assert cols["deletedAt"].is_nullable

    def test_parse_custom_schema(self):
        """Test parsing with custom default schema."""
        ddl = """
        CREATE TABLE users (
            id integer PRIMARY KEY
        )
        """
        tables = parse_ddl(ddl, default_schema="myschema")

        assert tables[0].schema_name == "myschema"

    def test_parse_explicit_schema_overrides_default(self):
        """Test that explicit schema in DDL overrides default."""
        ddl = """
        CREATE TABLE "custom"."users" (
            id integer PRIMARY KEY
        )
        """
        tables = parse_ddl(ddl, default_schema="public")

        assert tables[0].schema_name == "custom"

    def test_parse_unique_constraint(self):
        """Test that UNIQUE constraints are skipped correctly."""
        ddl = """
        CREATE TABLE users (
            id integer PRIMARY KEY,
            email varchar(255),
            UNIQUE (email)
        )
        """
        tables = parse_ddl(ddl)

        # Should only have 2 columns, not treat UNIQUE as a column
        assert len(tables[0].columns) == 2

    def test_parse_check_constraint(self):
        """Test that CHECK constraints are skipped correctly."""
        ddl = """
        CREATE TABLE products (
            id integer PRIMARY KEY,
            price decimal(10,2),
            CHECK (price > 0)
        )
        """
        tables = parse_ddl(ddl)

        assert len(tables[0].columns) == 2

    def test_parse_nested_parentheses_in_default(self):
        """Test parsing DEFAULT with nested function calls."""
        ddl = """
        CREATE TABLE logs (
            id integer,
            data jsonb DEFAULT jsonb_build_object('key', 'value')
        )
        """
        tables = parse_ddl(ddl)

        data_col = next(c for c in tables[0].columns if c.name == "data")
        assert "jsonb_build_object" in data_col.default_value

    def test_parse_empty_ddl(self):
        """Test parsing empty DDL returns empty list."""
        tables = parse_ddl("")
        assert tables == []

    def test_parse_no_tables(self):
        """Test parsing DDL with no CREATE TABLE statements."""
        ddl = "CREATE INDEX idx_users_email ON users(email);"
        tables = parse_ddl(ddl)
        assert tables == []

    def test_data_types_are_lowercase(self):
        """Test that data types are normalized to lowercase."""
        ddl = """
        CREATE TABLE test (
            id INTEGER,
            name VARCHAR(255),
            created TIMESTAMP WITH TIME ZONE
        )
        """
        tables = parse_ddl(ddl)

        cols = {c.name: c for c in tables[0].columns}
        assert cols["id"].data_type == "integer"
        assert cols["name"].data_type == "varchar(255)"
        assert cols["created"].data_type == "timestamp with time zone"


class TestParsedColumn:
    """Test ParsedColumn dataclass."""

    def test_column_defaults(self):
        """Test ParsedColumn default values."""
        col = ParsedColumn(
            name="test",
            data_type="integer",
            is_nullable=True,
            is_primary_key=False,
            is_foreign_key=False,
            foreign_key_table=None,
            foreign_key_column=None,
            default_value=None,
        )
        assert col.description is None

    def test_column_with_all_fields(self):
        """Test ParsedColumn with all fields set."""
        col = ParsedColumn(
            name="user_id",
            data_type="integer",
            is_nullable=False,
            is_primary_key=False,
            is_foreign_key=True,
            foreign_key_table="users",
            foreign_key_column="id",
            default_value=None,
            description="Reference to users table",
        )
        assert col.foreign_key_table == "users"
        assert col.description == "Reference to users table"


class TestParsedTable:
    """Test ParsedTable dataclass."""

    def test_table_defaults(self):
        """Test ParsedTable default values."""
        table = ParsedTable(
            schema_name="public",
            table_name="test",
            columns=[],
        )
        assert table.primary_key_columns == []
        assert table.foreign_keys == []
        assert table.description is None


class TestParsedForeignKey:
    """Test ParsedForeignKey dataclass."""

    def test_foreign_key_creation(self):
        """Test creating a ParsedForeignKey."""
        fk = ParsedForeignKey(
            from_column="user_id",
            to_table="users",
            to_column="id",
        )
        assert fk.from_column == "user_id"
        assert fk.to_table == "users"
        assert fk.to_column == "id"
