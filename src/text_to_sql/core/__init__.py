"""Core module with exceptions and type definitions."""

from text_to_sql.core.exceptions import (
    DatabaseConnectionError,
    SQLExecutionError,
    SQLValidationError,
    TextToSQLError,
    VectorStoreError,
)
from text_to_sql.core.types import SQLCategory, ValidationResult

__all__ = [
    "TextToSQLError",
    "SQLValidationError",
    "SQLExecutionError",
    "DatabaseConnectionError",
    "VectorStoreError",
    "SQLCategory",
    "ValidationResult",
]
