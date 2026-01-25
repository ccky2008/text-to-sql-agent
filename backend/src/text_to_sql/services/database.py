"""PostgreSQL database service using asyncpg."""

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

import asyncpg

from text_to_sql.config import get_settings
from text_to_sql.core.exceptions import DatabaseConnectionError, SQLExecutionError
from text_to_sql.core.types import ExecutionResult
from text_to_sql.models.data_sources import ColumnInfo, Relationship, TableInfo


class DatabaseService:
    """Service for PostgreSQL database operations."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._pool: asyncpg.Pool | None = None

    async def connect(self) -> None:
        """Initialize connection pool."""
        try:
            self._pool = await asyncpg.create_pool(
                host=self._settings.postgres_host,
                port=self._settings.postgres_port,
                database=self._settings.postgres_database,
                user=self._settings.postgres_user,
                password=self._settings.postgres_password.get_secret_value(),
                min_size=2,
                max_size=10,
                command_timeout=self._settings.sql_timeout_seconds,
            )
        except Exception as e:
            raise DatabaseConnectionError(f"Failed to connect to database: {e}") from e

    async def close(self) -> None:
        """Close connection pool."""
        if self._pool:
            await self._pool.close()
            self._pool = None

    @asynccontextmanager
    async def get_connection(self) -> AsyncGenerator[asyncpg.Connection, None]:
        """Get a connection from the pool."""
        if not self._pool:
            await self.connect()
        async with self._pool.acquire() as connection:  # type: ignore
            yield connection

    async def execute_query(
        self, sql: str, max_rows: int | None = None
    ) -> ExecutionResult:
        """Execute a SQL query and return results."""
        max_rows = max_rows or self._settings.sql_max_rows
        try:
            async with self.get_connection() as conn:
                # Use LIMIT wrapper for safety
                limited_sql = f"SELECT * FROM ({sql}) AS subq LIMIT {max_rows}"
                try:
                    rows = await conn.fetch(limited_sql)
                except asyncpg.PostgresSyntaxError:
                    # If wrapping fails, try original SQL
                    rows = await conn.fetch(sql)

                if rows:
                    columns = list(rows[0].keys())
                    results = [dict(row) for row in rows]
                    return ExecutionResult(
                        success=True,
                        rows=results,
                        row_count=len(results),
                        columns=columns,
                        error=None,
                    )
                return ExecutionResult(
                    success=True,
                    rows=[],
                    row_count=0,
                    columns=[],
                    error=None,
                )
        except asyncpg.PostgresError as e:
            return ExecutionResult(
                success=False,
                rows=None,
                row_count=0,
                columns=None,
                error=str(e),
            )
        except Exception as e:
            raise SQLExecutionError(f"Query execution failed: {e}", sql=sql) from e

    async def get_table_names(self, schema: str = "public") -> list[str]:
        """Get all table names in a schema."""
        query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = $1
            AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, schema)
            return [row["table_name"] for row in rows]

    async def get_table_info(self, table_name: str, schema: str = "public") -> TableInfo:
        """Get detailed information about a table."""
        columns = await self._get_columns(table_name, schema)
        relationships = await self._get_relationships(table_name, schema)
        description = await self._get_table_comment(table_name, schema)
        row_count = await self._get_row_count(table_name, schema)

        return TableInfo(
            schema_name=schema,
            table_name=table_name,
            columns=columns,
            relationships=relationships,
            description=description,
            row_count=row_count,
        )

    async def _get_columns(self, table_name: str, schema: str) -> list[ColumnInfo]:
        """Get column information for a table."""
        query = """
            SELECT
                c.column_name,
                c.data_type,
                c.is_nullable,
                c.column_default,
                c.udt_name,
                (
                    SELECT COUNT(*) > 0
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_schema = c.table_schema
                    AND tc.table_name = c.table_name
                    AND kcu.column_name = c.column_name
                    AND tc.constraint_type = 'PRIMARY KEY'
                ) as is_primary_key,
                (
                    SELECT COUNT(*) > 0
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                    WHERE tc.table_schema = c.table_schema
                    AND tc.table_name = c.table_name
                    AND kcu.column_name = c.column_name
                    AND tc.constraint_type = 'FOREIGN KEY'
                ) as is_foreign_key,
                pgd.description as column_comment
            FROM information_schema.columns c
            LEFT JOIN pg_catalog.pg_statio_all_tables st
                ON c.table_schema = st.schemaname AND c.table_name = st.relname
            LEFT JOIN pg_catalog.pg_description pgd
                ON pgd.objoid = st.relid
                AND pgd.objsubid = c.ordinal_position
            WHERE c.table_schema = $1 AND c.table_name = $2
            ORDER BY c.ordinal_position
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, schema, table_name)
            columns = []
            for row in rows:
                col = ColumnInfo(
                    name=row["column_name"],
                    data_type=row["data_type"],
                    is_nullable=row["is_nullable"] == "YES",
                    is_primary_key=row["is_primary_key"],
                    is_foreign_key=row["is_foreign_key"],
                    default_value=row["column_default"],
                    description=row["column_comment"],
                )
                columns.append(col)
            return columns

    async def _get_relationships(self, table_name: str, schema: str) -> list[Relationship]:
        """Get foreign key relationships for a table."""
        query = """
            SELECT
                kcu.column_name as from_column,
                ccu.table_name as to_table,
                ccu.column_name as to_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
            AND tc.table_schema = $1
            AND tc.table_name = $2
        """
        async with self.get_connection() as conn:
            rows = await conn.fetch(query, schema, table_name)
            return [
                Relationship(
                    from_table=table_name,
                    from_column=row["from_column"],
                    to_table=row["to_table"],
                    to_column=row["to_column"],
                    relationship_type="many-to-one",
                )
                for row in rows
            ]

    async def _get_table_comment(self, table_name: str, schema: str) -> str | None:
        """Get table comment/description."""
        query = """
            SELECT obj_description(
                (quote_ident($1) || '.' || quote_ident($2))::regclass::oid
            ) as comment
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, schema, table_name)
            return row["comment"] if row else None

    async def _get_row_count(self, table_name: str, schema: str) -> int | None:
        """Get approximate row count from pg_stat."""
        query = """
            SELECT n_live_tup as count
            FROM pg_stat_user_tables
            WHERE schemaname = $1 AND relname = $2
        """
        async with self.get_connection() as conn:
            row = await conn.fetchrow(query, schema, table_name)
            return row["count"] if row else None

    async def introspect_all(self, schema: str = "public") -> list[TableInfo]:
        """Introspect all tables in a schema."""
        table_names = await self.get_table_names(schema)
        tables = []
        for table_name in table_names:
            table_info = await self.get_table_info(table_name, schema)
            tables.append(table_info)
        return tables

    async def test_connection(self) -> bool:
        """Test database connection."""
        try:
            async with self.get_connection() as conn:
                await conn.fetchval("SELECT 1")
            return True
        except Exception:
            return False


_database_service: DatabaseService | None = None


def get_database_service() -> DatabaseService:
    """Get singleton database service instance."""
    global _database_service
    if _database_service is None:
        _database_service = DatabaseService()
    return _database_service


async def init_database_service() -> DatabaseService:
    """Initialize and return database service."""
    service = get_database_service()
    await service.connect()
    return service
