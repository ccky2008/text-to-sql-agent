"""Database schema introspection tools."""

from typing import Any

from langchain_core.tools import tool

from text_to_sql.services.database import get_database_service
from text_to_sql.services.vector_store import get_vector_store_service


@tool
async def list_tables(db_schema: str = "public") -> list[str]:
    """List all tables in the database schema.

    Args:
        db_schema: The database schema to list tables from (default: public)

    Returns:
        List of table names
    """
    db_service = get_database_service()
    return await db_service.get_table_names(db_schema)


@tool
async def get_table_schema(table_name: str, db_schema: str = "public") -> dict[str, Any]:
    """Get detailed schema information for a specific table.

    Args:
        table_name: Name of the table
        db_schema: The database schema (default: public)

    Returns:
        Table schema with columns, types, constraints, and relationships
    """
    db_service = get_database_service()
    table_info = await db_service.get_table_info(table_name, db_schema)

    return {
        "table_name": table_info.table_name,
        "schema_name": table_info.schema_name,
        "full_name": table_info.full_name,
        "description": table_info.description,
        "row_count": table_info.row_count,
        "columns": [
            {
                "name": col.name,
                "data_type": col.data_type,
                "is_nullable": col.is_nullable,
                "is_primary_key": col.is_primary_key,
                "is_foreign_key": col.is_foreign_key,
                "foreign_key_table": col.foreign_key_table,
                "foreign_key_column": col.foreign_key_column,
                "default_value": col.default_value,
                "description": col.description,
            }
            for col in table_info.columns
        ],
        "relationships": [
            {
                "from_column": rel.from_column,
                "to_table": rel.to_table,
                "to_column": rel.to_column,
                "relationship_type": rel.relationship_type,
            }
            for rel in table_info.relationships
        ],
        "ddl": table_info.to_ddl(),
    }


@tool
def get_all_known_tables() -> list[dict[str, Any]]:
    """Get all tables that have been indexed in the vector store.

    Returns:
        List of known tables with their basic info
    """
    vector_store = get_vector_store_service()
    tables = vector_store.list_database_info(limit=1000)

    return [
        {
            "table_name": t["metadata"].get("full_name", ""),
            "columns": t["metadata"].get("column_names", "").split(","),
            "description": t["metadata"].get("description", ""),
        }
        for t in tables
    ]


def get_schema_tools() -> list:
    """Get all schema tools."""
    return [list_tables, get_table_schema, get_all_known_tables]
