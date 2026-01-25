"""SQL validation and execution tools."""

import re
from typing import Any

import sqlglot
from langchain_core.tools import tool

from text_to_sql.core.types import SQLCategory, ValidationResult
from text_to_sql.services.database import get_database_service
from text_to_sql.services.vector_store import get_vector_store_service

# Dangerous SQL patterns to block
DANGEROUS_PATTERNS = [
    r"\bDROP\b",
    r"\bDELETE\b",
    r"\bTRUNCATE\b",
    r"\bALTER\b",
    r"\bCREATE\b",
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bEXECUTE\b",
]


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

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, cleaned_sql, re.IGNORECASE):
            keyword = pattern.replace(r"\b", "").strip()
            errors.append(f"Dangerous SQL keyword detected: {keyword}")

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
                else:
                    errors.append(f"Only SELECT and WITH (CTE) statements are allowed, got: {stmt_key}")

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


def validate_tables_exist(sql: str) -> tuple[bool, list[str]]:
    """Check if tables referenced in SQL exist in the database info.

    Args:
        sql: The SQL query to check

    Returns:
        Tuple of (all_exist, missing_tables)
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
            return True, []

        # Check against database info
        vector_store = get_vector_store_service()
        db_tables = vector_store.list_database_info(limit=1000)
        known_tables = {
            t["metadata"].get("table_name", "").lower() for t in db_tables
        }

        missing = [t for t in tables_in_query if t not in known_tables]
        return len(missing) == 0, missing

    except Exception:
        # If parsing fails, skip table validation
        return True, []


@tool
def validate_sql_query(sql: str) -> dict[str, Any]:
    """Validate a SQL query for syntax and safety.

    Args:
        sql: The SQL query to validate

    Returns:
        Validation result with is_valid, errors, warnings, and statement_type
    """
    result = validate_sql(sql)

    # Also check table existence if basic validation passed
    tables_valid = True
    missing_tables: list[str] = []
    if result.is_valid:
        tables_valid, missing_tables = validate_tables_exist(sql)
        if not tables_valid:
            result = ValidationResult(
                is_valid=False,
                errors=[f"Unknown tables referenced: {', '.join(missing_tables)}"],
                warnings=result.warnings,
                statement_type=result.statement_type,
            )

    return {
        "is_valid": result.is_valid,
        "errors": result.errors,
        "warnings": result.warnings,
        "statement_type": result.statement_type.value,
    }


@tool
async def execute_sql_query(sql: str, max_rows: int = 100) -> dict[str, Any]:
    """Execute a SQL query against the database.

    Args:
        sql: The SQL query to execute (must be SELECT or WITH)
        max_rows: Maximum number of rows to return (default: 100)

    Returns:
        Query results with rows, columns, and row_count
    """
    # First validate
    validation = validate_sql(sql)
    if not validation.is_valid:
        return {
            "success": False,
            "error": f"Validation failed: {'; '.join(validation.errors)}",
            "rows": None,
            "columns": None,
            "row_count": 0,
        }

    # Execute
    db_service = get_database_service()
    result = await db_service.execute_query(sql, max_rows=max_rows)

    return {
        "success": result.success,
        "rows": result.rows,
        "columns": result.columns,
        "row_count": result.row_count,
        "error": result.error,
    }


def get_sql_tools() -> list:
    """Get all SQL tools."""
    return [validate_sql_query, execute_sql_query]
