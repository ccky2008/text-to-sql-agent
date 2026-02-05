"""SQL validation node."""

from text_to_sql.agents.state import AgentState
from text_to_sql.agents.streaming import get_writer
from text_to_sql.agents.tools.sql_tools import validate_sql, validate_tables_exist


def validator_node(state: AgentState) -> dict:
    """Validate the generated SQL query.

    Performs:
    1. Check for special response types (out-of-scope, read-only)
    2. Syntax validation using sqlglot
    3. Safety checks (no dangerous statements)
    4. Table existence verification
    """
    writer = get_writer()
    writer({"type": "step_started", "step": "validator", "label": "Validating SQL"})

    # Check if this is a special response (out-of-scope or read-only)
    special_type = state.get("special_response_type")
    if special_type:
        # Skip validation - response is already set by sql_generator
        return {
            "is_valid": False,
            "validation_errors": [],
            "validation_warnings": [],
        }

    sql = state.get("generated_sql")

    if not sql:
        return {
            "is_valid": False,
            "validation_errors": ["No SQL query was generated"],
            "validation_warnings": [],
        }

    # Run validation
    result = validate_sql(sql)

    # Collect errors and warnings
    errors = list(result.errors)
    warnings = list(result.warnings)

    # If basic validation passed, check table existence (now returns error, not warning)
    if result.is_valid:
        tables_valid, missing_tables, table_error = validate_tables_exist(sql)
        if not tables_valid and table_error:
            errors.append(table_error)
            return {
                "is_valid": False,
                "validation_errors": errors,
                "validation_warnings": warnings,
                "special_response_type": "RESOURCE_NOT_FOUND",
            }

    return {
        "is_valid": result.is_valid,
        "validation_errors": errors,
        "validation_warnings": warnings,
    }
