"""API request models."""

from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    """Request model for the query endpoint."""

    question: str = Field(..., description="Natural language question to convert to SQL")
    session_id: str | None = Field(
        default=None, description="Optional session ID for conversation continuity"
    )
    execute: bool = Field(default=True, description="Whether to execute the generated SQL")
    stream: bool = Field(default=True, description="Whether to stream the response")


class SQLPairAddRequest(BaseModel):
    """Request to add a SQL pair."""

    question: str = Field(..., description="Natural language question")
    sql_query: str = Field(..., description="SQL query")


class MetadataAddRequest(BaseModel):
    """Request to add metadata."""

    title: str = Field(..., description="Title")
    content: str = Field(..., description="Content")
    category: str = Field(..., description="Category: business_rule, domain_term, or context")
    related_tables: list[str] = Field(default_factory=list, description="Related tables")
    keywords: list[str] = Field(default_factory=list, description="Keywords")


class TableInfoAddRequest(BaseModel):
    """Request to add table info."""

    schema_name: str = Field(default="public", description="Schema name")
    table_name: str = Field(..., description="Table name")
    columns: list[dict] = Field(..., description="Column definitions")
    description: str | None = Field(default=None, description="Table description")
