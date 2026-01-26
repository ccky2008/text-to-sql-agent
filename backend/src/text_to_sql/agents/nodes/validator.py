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

    # Collect warnings
    warnings = list(result.warnings)

    # If basic validation passed, check table existence (as warning, not error)
    if result.is_valid:
        tables_valid, missing_tables = validate_tables_exist(sql)
        if not tables_valid:
            # Add as warning instead of error - the executor will catch
            # actual missing tables when running against the database
            warnings.append(
                f"Tables not in metadata catalog: {', '.join(missing_tables)}. "
                "Query will still be executed."
            )

    return {
        "is_valid": result.is_valid,
        "validation_errors": result.errors,
        "validation_warnings": warnings,
    }
