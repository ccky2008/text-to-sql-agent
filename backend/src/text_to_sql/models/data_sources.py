"""Data source models for SQL pairs, metadata, and database info."""

import hashlib
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from pydantic import BaseModel, Field, model_validator

from text_to_sql.core.types import MetadataCategory

if TYPE_CHECKING:
    from collections.abc import Sequence


class SQLPair(BaseModel):
    """A question/SQL query pair for few-shot learning."""

    id: str = Field(default="", description="Deterministic ID based on question")
    question: str = Field(..., description="Natural language question")
    sql_query: str = Field(..., description="Corresponding SQL query")

    @model_validator(mode="after")
    def set_deterministic_id(self) -> "SQLPair":
        """Generate deterministic ID from question."""
        if not self.id:
            self.id = hashlib.sha256(self.question.encode()).hexdigest()[:16]
        return self

    def to_embedding_text(self) -> str:
        """Generate text for embedding."""
        return f"Question: {self.question}\nSQL: {self.sql_query}"

    def to_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata format."""
        return {
            "id": self.id,
            "question": self.question,
            "sql_query": self.sql_query,
        }


class MetadataEntry(BaseModel):
    """Domain/business knowledge metadata."""

    id: str = Field(default="", description="Deterministic ID based on title")
    title: str = Field(..., description="Title of the metadata entry")
    content: str = Field(..., description="Content/description")
    category: MetadataCategory = Field(..., description="Category of metadata")
    related_tables: list[str] = Field(default_factory=list, description="Related database tables")
    keywords: list[str] = Field(default_factory=list, description="Keywords for search")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def set_deterministic_id(self) -> "MetadataEntry":
        """Generate deterministic ID from title."""
        if not self.id:
            self.id = hashlib.sha256(self.title.encode()).hexdigest()[:16]
        return self

    def to_embedding_text(self) -> str:
        """Generate text for embedding."""
        parts = [f"Title: {self.title}", f"Content: {self.content}"]
        if self.keywords:
            parts.append(f"Keywords: {', '.join(self.keywords)}")
        return "\n".join(parts)

    def to_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata format."""
        return {
            "id": self.id,
            "title": self.title,
            "content": self.content,
            "category": self.category.value,
            "related_tables": ",".join(self.related_tables),
            "keywords": ",".join(self.keywords),
            "created_at": self.created_at.isoformat(),
        }


class ColumnInfo(BaseModel):
    """Column information for a database table."""

    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type")
    is_nullable: bool = Field(default=True, description="Whether the column is nullable")
    is_primary_key: bool = Field(default=False, description="Whether this is a primary key")
    is_foreign_key: bool = Field(default=False, description="Whether this is a foreign key")
    foreign_key_table: str | None = Field(default=None, description="Referenced table if FK")
    foreign_key_column: str | None = Field(default=None, description="Referenced column if FK")
    default_value: str | None = Field(default=None, description="Default value")
    description: str | None = Field(default=None, description="Column description/comment")


class Relationship(BaseModel):
    """Table relationship information."""

    from_table: str = Field(..., description="Source table")
    from_column: str = Field(..., description="Source column")
    to_table: str = Field(..., description="Target table")
    to_column: str = Field(..., description="Target column")
    relationship_type: str = Field(default="many-to-one", description="Relationship type")


class TableInfo(BaseModel):
    """PostgreSQL table schema information."""

    id: str = Field(default="", description="Deterministic ID based on schema.table")
    schema_name: str = Field(default="public", description="Schema name")
    table_name: str = Field(..., description="Table name")
    columns: list[ColumnInfo] = Field(default_factory=list, description="Column information")
    relationships: list[Relationship] = Field(default_factory=list, description="Relationships")
    description: str | None = Field(default=None, description="Table description/comment")
    row_count: int | None = Field(default=None, description="Approximate row count")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def set_deterministic_id(self) -> "TableInfo":
        """Generate deterministic ID from schema and table name."""
        if not self.id:
            key = f"{self.schema_name}.{self.table_name}"
            self.id = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self

    @property
    def full_name(self) -> str:
        """Get fully qualified table name."""
        return f"{self.schema_name}.{self.table_name}"

    def _format_column(self, col: ColumnInfo) -> str:
        """Format a single column for embedding text."""
        col_str = f"  - {col.name} ({col.data_type})"
        if col.is_primary_key:
            col_str += " PRIMARY KEY"
        if col.is_foreign_key and col.foreign_key_table:
            col_str += f" REFERENCES {col.foreign_key_table}"
        if col.description:
            col_str += f" -- {col.description}"
        return col_str

    def _build_embedding_text(self, columns: "Sequence[ColumnInfo]") -> str:
        """Build embedding text from a list of columns."""
        parts = [f"Table: {self.full_name}"]
        if self.description:
            parts.append(f"Description: {self.description}")

        if columns:
            parts.append("Columns:")
            parts.extend(self._format_column(col) for col in columns)

        return "\n".join(parts)

    def to_embedding_text(self) -> str:
        """Generate text for embedding."""
        return self._build_embedding_text(self.columns)

    def to_metadata(self) -> dict[str, Any]:
        """Convert to ChromaDB metadata format."""
        import json

        columns_data = [
            {
                "name": c.name,
                "data_type": c.data_type,
                "is_nullable": c.is_nullable,
                "is_primary_key": c.is_primary_key,
                "is_foreign_key": c.is_foreign_key,
                "foreign_key_table": c.foreign_key_table,
                "foreign_key_column": c.foreign_key_column,
                "default_value": c.default_value,
                "description": c.description,
            }
            for c in self.columns
        ]

        relationships_data = [
            {
                "from_table": r.from_table,
                "from_column": r.from_column,
                "to_table": r.to_table,
                "to_column": r.to_column,
                "relationship_type": r.relationship_type,
            }
            for r in self.relationships
        ]

        return {
            "id": self.id,
            "schema_name": self.schema_name,
            "table_name": self.table_name,
            "full_name": self.full_name,
            "column_names": ",".join(c.name for c in self.columns),
            "column_count": len(self.columns),
            "columns_json": json.dumps(columns_data),
            "relationships_json": json.dumps(relationships_data),
            "has_relationships": len(self.relationships) > 0,
            "description": self.description or "",
            "row_count": self.row_count if self.row_count is not None else -1,
            "created_at": self.created_at.isoformat(),
        }

    def get_visible_columns(
        self, excluded: "frozenset[str] | None" = None
    ) -> "Sequence[ColumnInfo]":
        """Return columns excluding system columns.

        Args:
            excluded: Set of column names to exclude. If None, uses default
                      EXCLUDED_SELECT_COLUMNS from system_rules.

        Returns:
            List of columns not in the excluded set.
        """
        if excluded is None:
            from text_to_sql.services.system_rules import EXCLUDED_SELECT_COLUMNS

            excluded = EXCLUDED_SELECT_COLUMNS
        return [col for col in self.columns if col.name not in excluded]

    def to_embedding_text_filtered(
        self, excluded: "frozenset[str] | None" = None
    ) -> str:
        """Generate text for embedding without system columns.

        Args:
            excluded: Set of column names to exclude. If None, uses default
                      EXCLUDED_SELECT_COLUMNS from system_rules.

        Returns:
            Embedding text with filtered columns.
        """
        return self._build_embedding_text(self.get_visible_columns(excluded))

    def to_ddl(self) -> str:
        """Generate DDL-like representation."""
        lines = [f"CREATE TABLE {self.full_name} ("]
        col_lines = []
        for col in self.columns:
            col_def = f"  {col.name} {col.data_type}"
            if col.is_primary_key:
                col_def += " PRIMARY KEY"
            if not col.is_nullable:
                col_def += " NOT NULL"
            if col.default_value:
                col_def += f" DEFAULT {col.default_value}"
            col_lines.append(col_def)
        lines.append(",\n".join(col_lines))
        lines.append(");")
        return "\n".join(lines)
