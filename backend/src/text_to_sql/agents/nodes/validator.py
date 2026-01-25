"""SQL validation node."""

from text_to_sql.agents.state import AgentState
from text_to_sql.agents.tools.sql_tools import validate_sql, validate_tables_exist


def validator_node(state: AgentState) -> dict:
    """Validate the generated SQL query.

    Performs:
    1. Syntax validation using sqlglot
    2. Safety checks (no dangerous statements)
    3. Table existence verification
    """
    sql = state.get("generated_sql")

    if not sql:
        return {
            "is_valid": False,
            "validation_errors": ["No SQL query was generated"],
            "validation_warnings": [],
        }

    # Run validation
    result = validate_sql(sql)

    # If basic validation passed, check table existence
    if result.is_valid:
        tables_valid, missing_tables = validate_tables_exist(sql)
        if not tables_valid:
            return {
                "is_valid": False,
                "validation_errors": [
                    f"Unknown tables referenced: {', '.join(missing_tables)}"
                ],
                "validation_warnings": result.warnings,
            }

    return {
        "is_valid": result.is_valid,
        "validation_errors": result.errors,
        "validation_warnings": result.warnings,
    }
