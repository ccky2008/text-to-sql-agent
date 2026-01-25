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
