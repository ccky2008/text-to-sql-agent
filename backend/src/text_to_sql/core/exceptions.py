"""Custom exceptions for the text-to-sql agent."""


class TextToSQLError(Exception):
    """Base exception for text-to-sql agent errors."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}


class SQLValidationError(TextToSQLError):
    """Raised when SQL validation fails."""

    def __init__(self, message: str, sql: str | None = None, errors: list[str] | None = None):
        super().__init__(message, {"sql": sql, "errors": errors or []})
        self.sql = sql
        self.errors = errors or []


class SQLExecutionError(TextToSQLError):
    """Raised when SQL execution fails."""

    def __init__(self, message: str, sql: str | None = None, original_error: str | None = None):
        super().__init__(message, {"sql": sql, "original_error": original_error})
        self.sql = sql
        self.original_error = original_error


class DatabaseConnectionError(TextToSQLError):
    """Raised when database connection fails."""

    pass


class VectorStoreError(TextToSQLError):
    """Raised when vector store operations fail."""

    pass


class SessionNotFoundError(TextToSQLError):
    """Raised when a session is not found."""

    def __init__(self, session_id: str):
        super().__init__(f"Session not found: {session_id}", {"session_id": session_id})
        self.session_id = session_id


class EmbeddingError(TextToSQLError):
    """Raised when embedding generation fails."""

    pass
