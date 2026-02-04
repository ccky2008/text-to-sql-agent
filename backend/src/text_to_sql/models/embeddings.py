"""Pydantic models for embeddings API endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field

from text_to_sql.core.types import MetadataCategory


# ============================================================================
# SQL Pairs Models
# ============================================================================


class SQLPairCreate(BaseModel):
    """Request model for creating a SQL pair."""

    question: str = Field(..., description="Natural language question")
    sql_query: str = Field(..., description="Corresponding SQL query")


class SQLPairUpdate(BaseModel):
    """Request model for updating a SQL pair."""

    question: str | None = Field(None, description="Natural language question")
    sql_query: str | None = Field(None, description="Corresponding SQL query")


class SQLPairResponse(BaseModel):
    """Response model for a SQL pair."""

    id: str
    question: str
    sql_query: str


class SQLPairListResponse(BaseModel):
    """Response model for listing SQL pairs."""

    items: list[SQLPairResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


# ============================================================================
# Metadata Models
# ============================================================================


class MetadataCreate(BaseModel):
    """Request model for creating a metadata entry."""

    title: str = Field(..., description="Title of the metadata entry")
    content: str = Field(..., description="Content/description")
    category: MetadataCategory = Field(..., description="Category of metadata")
    related_tables: list[str] = Field(default_factory=list, description="Related database tables")
    keywords: list[str] = Field(default_factory=list, description="Keywords for search")


class MetadataUpdate(BaseModel):
    """Request model for updating a metadata entry."""

    title: str | None = Field(None, description="Title of the metadata entry")
    content: str | None = Field(None, description="Content/description")
    category: MetadataCategory | None = Field(None, description="Category of metadata")
    related_tables: list[str] | None = Field(None, description="Related database tables")
    keywords: list[str] | None = Field(None, description="Keywords for search")


class MetadataResponse(BaseModel):
    """Response model for a metadata entry."""

    id: str
    title: str
    content: str
    category: str
    related_tables: list[str]
    keywords: list[str]
    created_at: datetime | None = None


class MetadataListResponse(BaseModel):
    """Response model for listing metadata entries."""

    items: list[MetadataResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


# ============================================================================
# Database Info Models
# ============================================================================


class ColumnInfoCreate(BaseModel):
    """Request model for column information."""

    name: str = Field(..., description="Column name")
    data_type: str = Field(..., description="Data type")
    is_nullable: bool = Field(default=True, description="Whether the column is nullable")
    is_primary_key: bool = Field(default=False, description="Whether this is a primary key")
    is_foreign_key: bool = Field(default=False, description="Whether this is a foreign key")
    foreign_key_table: str | None = Field(default=None, description="Referenced table if FK")
    foreign_key_column: str | None = Field(default=None, description="Referenced column if FK")
    default_value: str | None = Field(default=None, description="Default value")
    description: str | None = Field(default=None, description="Column description/comment")


class RelationshipCreate(BaseModel):
    """Request model for table relationship."""

    from_table: str = Field(..., description="Source table")
    from_column: str = Field(..., description="Source column")
    to_table: str = Field(..., description="Target table")
    to_column: str = Field(..., description="Target column")
    relationship_type: str = Field(default="many-to-one", description="Relationship type")


class DatabaseInfoCreate(BaseModel):
    """Request model for creating database info."""

    schema_name: str = Field(default="public", description="Schema name")
    table_name: str = Field(..., description="Table name")
    columns: list[ColumnInfoCreate] = Field(default_factory=list, description="Column information")
    relationships: list[RelationshipCreate] = Field(default_factory=list, description="Relationships")
    description: str | None = Field(default=None, description="Table description/comment")
    row_count: int | None = Field(default=None, description="Approximate row count")


class DatabaseInfoUpdate(BaseModel):
    """Request model for updating database info."""

    schema_name: str | None = Field(None, description="Schema name")
    table_name: str | None = Field(None, description="Table name")
    columns: list[ColumnInfoCreate] | None = Field(None, description="Column information")
    relationships: list[RelationshipCreate] | None = Field(None, description="Relationships")
    description: str | None = Field(None, description="Table description/comment")
    row_count: int | None = Field(None, description="Approximate row count")


class ColumnInfoResponse(BaseModel):
    """Response model for column information."""

    name: str
    data_type: str
    is_nullable: bool
    is_primary_key: bool
    is_foreign_key: bool
    foreign_key_table: str | None
    foreign_key_column: str | None
    default_value: str | None
    description: str | None


class RelationshipResponse(BaseModel):
    """Response model for table relationship."""

    from_table: str
    from_column: str
    to_table: str
    to_column: str
    relationship_type: str


class DatabaseInfoResponse(BaseModel):
    """Response model for database info."""

    id: str
    schema_name: str
    table_name: str
    full_name: str
    columns: list[ColumnInfoResponse]
    relationships: list[RelationshipResponse]
    description: str | None
    row_count: int | None
    created_at: datetime | None = None


class DatabaseInfoListResponse(BaseModel):
    """Response model for listing database info."""

    items: list[DatabaseInfoResponse]
    total: int
    page: int
    page_size: int
    has_next: bool
    has_prev: bool


# ============================================================================
# DDL Import Models
# ============================================================================


class DDLImportRequest(BaseModel):
    """Request model for importing database schema from DDL statements."""

    ddl: str = Field(..., description="DDL statement(s) - CREATE TABLE statements")
    schema_name: str = Field(default="public", description="Default schema name if not in DDL")


class DDLImportResponse(BaseModel):
    """Response model for DDL import."""

    tables_imported: int
    tables: list[str]
    errors: list[str]


# ============================================================================
# Bulk Operation Models
# ============================================================================


class BulkCreateResponse(BaseModel):
    """Response model for bulk create operations."""

    created: int
    updated: int
    failed: int
    errors: list[str]


class BulkDeleteRequest(BaseModel):
    """Request model for bulk delete operations."""

    ids: list[str] = Field(..., description="List of IDs to delete")


class BulkDeleteResponse(BaseModel):
    """Response model for bulk delete operations."""

    deleted: int
    not_found: list[str]


class BulkUpdateItem(BaseModel):
    """Base model for bulk update items."""

    id: str = Field(..., description="ID of the item to update")


class SQLPairBulkUpdateItem(BulkUpdateItem):
    """Bulk update item for SQL pairs."""

    question: str | None = None
    sql_query: str | None = None


class MetadataBulkUpdateItem(BulkUpdateItem):
    """Bulk update item for metadata entries."""

    title: str | None = None
    content: str | None = None
    category: MetadataCategory | None = None
    related_tables: list[str] | None = None
    keywords: list[str] | None = None


class DatabaseInfoBulkUpdateItem(BulkUpdateItem):
    """Bulk update item for database info."""

    schema_name: str | None = None
    table_name: str | None = None
    columns: list[ColumnInfoCreate] | None = None
    relationships: list[RelationshipCreate] | None = None
    description: str | None = None
    row_count: int | None = None


class BulkUpdateResponse(BaseModel):
    """Response model for bulk update operations."""

    updated: int
    not_found: list[str]
    errors: list[str]
