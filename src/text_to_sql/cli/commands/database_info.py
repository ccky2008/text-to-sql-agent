"""Database info CLI commands."""

import asyncio
import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from text_to_sql.models.data_sources import ColumnInfo, TableInfo
from text_to_sql.services.database import get_database_service
from text_to_sql.services.vector_store import get_vector_store_service

app = typer.Typer(help="Manage database schema information")
console = Console()


@app.command("add")
def add_table_info(
    table_name: str = typer.Option(..., "-t", "--table-name", help="Table name"),
    schema_name: str = typer.Option("public", "-s", "--schema", help="Schema name"),
    columns_json: str = typer.Option(
        ...,
        "-c",
        "--columns",
        help='Columns as JSON array: [{"name": "id", "data_type": "integer"}]',
    ),
    description: str = typer.Option(None, "-d", "--description", help="Table description"),
):
    """Add table info manually to the vector store."""
    try:
        columns_data = json.loads(columns_json)
        columns = [
            ColumnInfo(
                name=col["name"],
                data_type=col.get("data_type", "text"),
                is_nullable=col.get("is_nullable", True),
                is_primary_key=col.get("is_primary_key", False),
                is_foreign_key=col.get("is_foreign_key", False),
                description=col.get("description"),
            )
            for col in columns_data
        ]
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON for columns: {e}[/red]")
        raise typer.Exit(1)

    table_info = TableInfo(
        schema_name=schema_name,
        table_name=table_name,
        columns=columns,
        description=description,
    )

    vector_store = get_vector_store_service()
    table_id, is_update = vector_store.add_table_info(table_info)

    if is_update:
        console.print(f"[cyan]Updated table info with ID: {table_id}[/cyan]")
    else:
        console.print(f"[green]Added table info with ID: {table_id}[/green]")


@app.command("introspect")
def introspect_database(
    schema: str = typer.Option("public", "-s", "--schema", help="Schema to introspect"),
    clear_existing: bool = typer.Option(
        False, "--clear", help="Clear existing database info before importing"
    ),
):
    """Introspect PostgreSQL database and import schema information."""

    async def _introspect():
        db_service = get_database_service()
        await db_service.connect()

        try:
            console.print(f"[blue]Introspecting schema: {schema}[/blue]")

            vector_store = get_vector_store_service()

            if clear_existing:
                console.print("[yellow]Clearing existing database info...[/yellow]")
                vector_store.clear_collection("database_info")

            tables = await db_service.introspect_all(schema)

            if not tables:
                console.print("[yellow]No tables found in schema[/yellow]")
                return

            console.print(f"[blue]Found {len(tables)} tables[/blue]")

            added_count = 0
            updated_count = 0
            for table in tables:
                _, is_update = vector_store.add_table_info(table)
                if is_update:
                    console.print(f"  [cyan]~ {table.full_name}[/cyan] ({len(table.columns)} columns) [updated]")
                    updated_count += 1
                else:
                    console.print(f"  [green]+ {table.full_name}[/green] ({len(table.columns)} columns)")
                    added_count += 1

            console.print(f"\n[green]Added {added_count} tables, updated {updated_count} tables[/green]")

        finally:
            await db_service.close()

    asyncio.run(_introspect())


@app.command("import-tables")
def import_tables(
    table_names: list[str] = typer.Argument(..., help="Table names to import"),
    schema: str = typer.Option("public", "-s", "--schema", help="Schema name"),
):
    """Import schema for specific tables from PostgreSQL database.

    Example:
        text-to-sql database-info import-tables users orders products
        text-to-sql database-info import-tables aws_ec2 aws_s3 -s public
    """

    async def _import_tables():
        db_service = get_database_service()
        await db_service.connect()

        try:
            vector_store = get_vector_store_service()

            # Get available tables for validation
            available_tables = await db_service.get_table_names(schema)

            added_count = 0
            updated_count = 0
            error_count = 0

            for table_name in table_names:
                if table_name not in available_tables:
                    console.print(f"  [yellow]! {table_name} not found in schema '{schema}'[/yellow]")
                    error_count += 1
                    continue

                try:
                    table_info = await db_service.get_table_info(table_name, schema)
                    _, is_update = vector_store.add_table_info(table_info)
                    if is_update:
                        console.print(
                            f"  [cyan]~ {table_info.full_name}[/cyan] ({len(table_info.columns)} columns) [updated]"
                        )
                        updated_count += 1
                    else:
                        console.print(
                            f"  [green]+ {table_info.full_name}[/green] ({len(table_info.columns)} columns)"
                        )
                        added_count += 1
                except Exception as e:
                    console.print(f"  [red]x {table_name}: {e}[/red]")
                    error_count += 1

            console.print(f"\n[green]Added {added_count} tables, updated {updated_count} tables[/green]")
            if error_count:
                console.print(f"[yellow]Failed to import {error_count} tables[/yellow]")

        finally:
            await db_service.close()

    asyncio.run(_import_tables())


@app.command("list")
def list_database_info(
    limit: int = typer.Option(20, "-n", "--limit", help="Number of tables to show"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
):
    """List all table info in the vector store."""
    vector_store = get_vector_store_service()
    tables = vector_store.list_database_info(limit=limit, offset=offset)
    total = vector_store.get_database_info_count()

    if not tables:
        console.print("[yellow]No database info found. Run 'db-info introspect' first.[/yellow]")
        return

    table = Table(title=f"Database Tables ({len(tables)} of {total})")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Table Name")
    table.add_column("Columns")
    table.add_column("Description", max_width=40)

    for t in tables:
        meta = t.get("metadata", {})
        table.add_row(
            meta.get("id", "")[:8],
            meta.get("full_name", ""),
            str(meta.get("column_count", 0)),
            meta.get("description", "")[:40] or "-",
        )

    console.print(table)


@app.command("show")
def show_table_info(
    table_name: str = typer.Argument(..., help="Table name to show details for"),
):
    """Show detailed information about a specific table."""
    vector_store = get_vector_store_service()
    tables = vector_store.list_database_info(limit=1000)

    # Find the table
    found = None
    for t in tables:
        meta = t.get("metadata", {})
        if meta.get("table_name") == table_name or meta.get("full_name") == table_name:
            found = t
            break

    if not found:
        console.print(f"[red]Table not found: {table_name}[/red]")
        raise typer.Exit(1)

    console.print(f"\n[bold]Table: {found['metadata'].get('full_name')}[/bold]")
    if found["metadata"].get("description"):
        console.print(f"Description: {found['metadata']['description']}")

    console.print(f"\n[blue]Schema (DDL-like):[/blue]")
    console.print(found.get("document", ""))


@app.command("search")
def search_database_info(
    query: str = typer.Argument(..., help="Search query"),
    n_results: int = typer.Option(5, "-n", help="Number of results"),
):
    """Search for relevant database schema information."""
    vector_store = get_vector_store_service()
    results = vector_store.search_database_info(query, n_results=n_results)

    if not results:
        console.print("[yellow]No matching tables found[/yellow]")
        return

    for i, result in enumerate(results, 1):
        meta = result.get("metadata", {})
        distance = result.get("distance", 0)
        similarity = 1 - distance if distance else 0

        console.print(f"\n[bold]Result {i}[/bold] (similarity: {similarity:.2%})")
        console.print(f"[blue]Table:[/blue] {meta.get('full_name', '')}")
        console.print(f"[green]Columns:[/green] {meta.get('column_names', '')}")
        if meta.get("description"):
            console.print(f"[dim]Description:[/dim] {meta.get('description')}")


@app.command("delete")
def delete_table_info(
    table_id: str = typer.Argument(..., help="ID of the table info to delete"),
):
    """Delete table info by ID."""
    vector_store = get_vector_store_service()
    vector_store.delete_table_info(table_id)
    console.print(f"[green]Deleted table info: {table_id}[/green]")


@app.command("clear")
def clear_database_info(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear all database info from the vector store."""
    if not confirm:
        confirm = typer.confirm("Are you sure you want to delete all database info?")

    if confirm:
        vector_store = get_vector_store_service()
        vector_store.clear_collection("database_info")
        console.print("[green]Cleared all database info[/green]")
    else:
        console.print("[yellow]Cancelled[/yellow]")
