"""Type definitions for the text-to-sql agent."""

from enum import Enum
from typing import NamedTuple


class SQLCategory(str, Enum):
    """Categories for SQL statement classification."""

    SELECT = "select"
    INSERT = "insert"
    UPDATE = "update"
    DELETE = "delete"
    CREATE = "create"
    ALTER = "alter"
    DROP = "drop"
    WITH = "with"  # CTE
    UNKNOWN = "unknown"


class MetadataCategory(str, Enum):
    """Categories for metadata entries."""

    BUSINESS_RULE = "business_rule"
    DOMAIN_TERM = "domain_term"
    CONTEXT = "context"


class ValidationResult(NamedTuple):
    """Result of SQL validation."""

    is_valid: bool
    errors: list[str]
    warnings: list[str]
    statement_type: SQLCategory


class ExecutionResult(NamedTuple):
    """Result of SQL execution."""

    success: bool
    rows: list[dict] | None
    row_count: int
    columns: list[str] | None
    error: str | None


class ToolExecutionResult(NamedTuple):
    """Result of SQL tool execution with pagination support.

    This type is used by the execute_sql_query tool to return
    results that can be displayed as interactive tables.
    """

    success: bool
    rows: list[dict] | None
    columns: list[str] | None
    row_count: int  # Number of rows in current page
    total_count: int | None  # Total rows matching query (for pagination)
    has_more: bool  # Whether more rows exist beyond current page
    page: int  # Current page number (1-indexed)
    page_size: int  # Number of rows per page
    query_token: str | None  # Token for CSV download
    error: str | None
