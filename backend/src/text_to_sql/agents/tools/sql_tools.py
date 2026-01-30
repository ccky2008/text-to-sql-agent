"""SQL validation and execution tools."""

import re
from typing import Any

import sqlglot
from langchain_core.tools import tool

from text_to_sql.config import get_settings
from text_to_sql.core.types import SQLCategory, ValidationResult
from text_to_sql.services.database import get_database_service
from text_to_sql.services.query_cache import get_query_cache
from text_to_sql.services.vector_store import get_vector_store_service

# User-friendly error messages for prohibited SQL operations
PROHIBITED_OPERATIONS = {
    "DROP": "This system is read-only. Dropping tables or database objects is not supported.",
    "DELETE": "This system is read-only. Deleting data is not permitted.",
    "TRUNCATE": "This system is read-only. Truncating tables is not permitted.",
    "ALTER": "This system is read-only. Altering database schema is not permitted.",
    "CREATE": "This system is read-only. Creating new database objects is not permitted.",
    "INSERT": "This system is read-only. Adding new data is not permitted.",
    "UPDATE": "This system is read-only. Modifying existing data is not permitted.",
    "GRANT": "This system is read-only. Changing permissions is not permitted.",
    "REVOKE": "This system is read-only. Changing permissions is not permitted.",
    "EXEC": "This system is read-only. Executing stored procedures is not permitted.",
    "EXECUTE": "This system is read-only. Executing stored procedures is not permitted.",
}


def validate_sql(sql: str) -> ValidationResult:
    """Validate SQL query for safety and syntax.

    Args:
        sql: The SQL query to validate

    Returns:
        ValidationResult with is_valid, errors, warnings, and statement_type
    """
    errors: list[str] = []
    warnings: list[str] = []
    statement_type = SQLCategory.UNKNOWN

    # Remove comments and normalize whitespace
    cleaned_sql = re.sub(r"--.*$", "", sql, flags=re.MULTILINE)
    cleaned_sql = re.sub(r"/\*.*?\*/", "", cleaned_sql, flags=re.DOTALL)
    cleaned_sql = " ".join(cleaned_sql.split())

    # Check for dangerous patterns and provide user-friendly messages
    for keyword, message in PROHIBITED_OPERATIONS.items():
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            errors.append(message)
            # Add helpful suggestion only once
            if not any("You can only query" in e for e in errors):
                errors.append(
                    "You can only query (SELECT) cloud resource data. "
                    "How can I help you find information about your cloud resources?"
                )

    if errors:
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            statement_type=statement_type,
        )

    # Parse with sqlglot for syntax validation
    try:
        parsed = sqlglot.parse(sql, dialect="postgres")
        if not parsed:
            errors.append("Failed to parse SQL: empty result")
        else:
            for stmt in parsed:
                if stmt is None:
                    continue

                # Determine statement type
                stmt_key = stmt.key.upper() if hasattr(stmt, "key") else ""
                if stmt_key == "SELECT":
                    statement_type = SQLCategory.SELECT
                elif stmt_key == "WITH":
                    statement_type = SQLCategory.WITH
                elif stmt_key == "SEMICOLON":
                    # Skip trailing semicolons (from SQL ending with `;` followed by comment)
                    continue
                else:
                    errors.append(
                        f"Only SELECT and WITH (CTE) statements are allowed, got: {stmt_key}"
                    )

    except sqlglot.errors.ParseError as e:
        errors.append(f"SQL syntax error: {e}")
    except Exception as e:
        errors.append(f"SQL parsing failed: {e}")

    if errors:
        return ValidationResult(
            is_valid=False,
            errors=errors,
            warnings=warnings,
            statement_type=statement_type,
        )

    # Check for warnings
    upper_sql = cleaned_sql.upper()
    if "SELECT *" in upper_sql:
        warnings.append("Using SELECT * is not recommended; specify columns explicitly")

    if "LIMIT" not in upper_sql:
        warnings.append("Query has no LIMIT clause; large result sets may impact performance")

    return ValidationResult(
        is_valid=True,
        errors=errors,
        warnings=warnings,
        statement_type=statement_type,
    )


def validate_tables_exist(sql: str) -> tuple[bool, list[str], str | None]:
    """Check if tables referenced in SQL exist in the database info.

    Args:
        sql: The SQL query to check

    Returns:
        Tuple of (all_exist, missing_tables, user_friendly_error)
    """
    try:
        parsed = sqlglot.parse(sql, dialect="postgres")
        tables_in_query = set()

        for stmt in parsed:
            if stmt is None:
                continue
            # Extract table names from the query
            for table in stmt.find_all(sqlglot.exp.Table):
                table_name = table.name
                if table_name:
                    tables_in_query.add(table_name.lower())

        if not tables_in_query:
            return True, [], None

        # Check against database info
        vector_store = get_vector_store_service()
        db_tables = vector_store.list_database_info(limit=1000)
        known_tables = {
            t["metadata"].get("table_name", "").lower() for t in db_tables
        }

        missing = [t for t in tables_in_query if t not in known_tables]

        if missing:
            # Generate user-friendly error message
            if len(missing) == 1:
                error_msg = (
                    f"The requested resource type '{missing[0]}' does not exist in our database. "
                    "We cannot provide information about resources that are not tracked. "
                    "Please try asking about a different resource type."
                )
            else:
                tables_list = ", ".join(f"'{t}'" for t in missing)
                error_msg = (
                    f"The requested resource types ({tables_list}) do not exist in our database. "
                    "We cannot provide information about resources that are not tracked. "
                    "Please try asking about different resource types."
                )
            return False, missing, error_msg

        return True, [], None

    except Exception:
        # If parsing fails, skip table validation
        return True, [], None


@tool
def validate_sql_query(sql: str) -> dict[str, Any]:
    """Validate a SQL query for syntax and safety.

    Args:
        sql: The SQL query to validate

    Returns:
        Validation result with is_valid, errors, warnings, and statement_type
    """
    result = validate_sql(sql)
    errors = list(result.errors)
    warnings = list(result.warnings)

    # Check table existence if basic validation passed
    if result.is_valid:
        tables_valid, _, table_error = validate_tables_exist(sql)
        if not tables_valid and table_error:
            errors.append(table_error)

    # Query is valid only if syntax validation passed AND no table errors were added
    is_valid = result.is_valid and len(errors) == 0

    return {
        "is_valid": is_valid,
        "errors": errors,
        "warnings": warnings,
        "statement_type": result.statement_type.value,
    }


@tool
async def execute_sql_query(
    sql: str,
    page: int = 1,
    page_size: int = 100,
    session_id: str = "default",
) -> dict[str, Any]:
    """Execute a SQL query against the database and return paginated results.

    This tool executes validated SQL queries and returns results suitable for
    displaying in interactive tables. Results are paginated and include a
    query token for CSV downloads.

    Args:
        sql: The SQL query to execute (must be SELECT or WITH)
        page: Page number to retrieve (1-indexed, default: 1)
        page_size: Number of rows per page (default: 100, max: 500)
        session_id: Session identifier for query caching (default: "default")

    Returns:
        Query results with rows, columns, pagination info, and query_token
    """
    settings = get_settings()

    # Enforce page_size limits
    page_size = min(page_size, 500)
    page_size = max(page_size, 1)
    page = max(page, 1)

    # First validate
    validation = validate_sql(sql)
    if not validation.is_valid:
        return _error_result(
            f"Validation failed: {'; '.join(validation.errors)}",
            page=page,
            page_size=page_size,
        )

    # Check table existence
    tables_valid, _, table_error = validate_tables_exist(sql)
    if not tables_valid and table_error:
        return _error_result(table_error, page=page, page_size=page_size)

    db_service = get_database_service()

    # Get total count for pagination (with timeout to avoid blocking)
    total_count = await db_service.execute_count_query(sql, timeout=5.0)

    # Cap page number to prevent extremely large offsets
    max_page = 10000
    page = min(page, max_page)

    # Calculate offset
    offset = (page - 1) * page_size

    # Enforce max rows limit
    effective_page_size = min(page_size, settings.sql_max_rows)

    # Execute paginated query
    result = await db_service.execute_query_paginated(
        sql, offset=offset, limit=effective_page_size
    )

    if not result.success:
        return _error_result(
            result.error or "Query execution failed",
            page=page,
            page_size=page_size,
        )

    # Determine if there are more results
    has_more = False
    if total_count is not None:
        has_more = (offset + result.row_count) < total_count
    elif result.row_count == effective_page_size:
        # If we got a full page, there might be more
        has_more = True

    # Generate query token for CSV downloads
    query_cache = get_query_cache()
    query_token = query_cache.store(sql, session_id)

    return {
        "success": True,
        "rows": result.rows,
        "columns": result.columns,
        "row_count": result.row_count,
        "total_count": total_count,
        "has_more": has_more,
        "page": page,
        "page_size": page_size,
        "query_token": query_token,
        "error": None,
    }


def _error_result(error: str, page: int = 1, page_size: int = 100) -> dict[str, Any]:
    """Create an error result dictionary."""
    return {
        "success": False,
        "rows": None,
        "columns": None,
        "row_count": 0,
        "total_count": None,
        "has_more": False,
        "page": page,
        "page_size": page_size,
        "query_token": None,
        "error": error,
    }


def get_sql_tools() -> list:
    """Get all SQL tools."""
    return [validate_sql_query, execute_sql_query]
