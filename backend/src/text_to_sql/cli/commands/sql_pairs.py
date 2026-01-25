"""SQL pairs CLI commands."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from text_to_sql.models.data_sources import SQLPair
from text_to_sql.services.vector_store import get_vector_store_service

app = typer.Typer(help="Manage SQL pair examples for few-shot learning")
console = Console()


@app.command("add")
def add_sql_pair(
    question: str = typer.Option(..., "-q", "--question", help="Natural language question"),
    sql: str = typer.Option(..., "-s", "--sql", help="SQL query"),
):
    """Add a new SQL pair to the vector store."""
    pair = SQLPair(question=question, sql_query=sql)

    vector_store = get_vector_store_service()
    pair_id, is_update = vector_store.add_sql_pair(pair)

    if is_update:
        console.print(f"[cyan]Updated SQL pair with ID: {pair_id}[/cyan]")
    else:
        console.print(f"[green]Added SQL pair with ID: {pair_id}[/green]")


@app.command("import")
def import_sql_pairs(
    file_path: Path = typer.Argument(..., help="Path to JSON file with SQL pairs"),
):
    """Import SQL pairs from a JSON file.

    Expected format:
    [
        {"question": "...", "sql_query": "..."},
        {"question": "...", "sql_query": "..."}
    ]
    """
    if not file_path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)

    with open(file_path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        console.print("[red]JSON must be an array of SQL pair objects[/red]")
        raise typer.Exit(1)

    vector_store = get_vector_store_service()
    added_count = 0
    updated_count = 0
    error_count = 0

    for item in data:
        try:
            pair = SQLPair(question=item["question"], sql_query=item["sql_query"])
            _, is_update = vector_store.add_sql_pair(pair)
            if is_update:
                updated_count += 1
            else:
                added_count += 1
        except Exception as e:
            console.print(f"[yellow]Error importing pair: {e}[/yellow]")
            error_count += 1

    console.print(f"[green]Added {added_count} SQL pairs, updated {updated_count} SQL pairs[/green]")
    if error_count:
        console.print(f"[yellow]Failed to import {error_count} pairs[/yellow]")


@app.command("list")
def list_sql_pairs(
    limit: int = typer.Option(20, "-n", "--limit", help="Number of pairs to show"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
):
    """List all SQL pairs in the vector store."""
    vector_store = get_vector_store_service()
    pairs = vector_store.list_sql_pairs(limit=limit, offset=offset)
    total = vector_store.get_sql_pairs_count()

    if not pairs:
        console.print("[yellow]No SQL pairs found[/yellow]")
        return

    table = Table(title=f"SQL Pairs ({len(pairs)} of {total})")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Question", max_width=50)
    table.add_column("SQL", max_width=50)

    for pair in pairs:
        meta = pair.get("metadata", {})
        table.add_row(
            meta.get("id", "")[:8],
            meta.get("question", "")[:50],
            meta.get("sql_query", "")[:50],
        )

    console.print(table)


@app.command("search")
def search_sql_pairs(
    query: str = typer.Argument(..., help="Search query"),
    n_results: int = typer.Option(5, "-n", help="Number of results"),
):
    """Search for similar SQL pairs."""
    vector_store = get_vector_store_service()
    results = vector_store.search_sql_pairs(query, n_results=n_results)

    if not results:
        console.print("[yellow]No matching SQL pairs found[/yellow]")
        return

    for i, result in enumerate(results, 1):
        meta = result.get("metadata", {})
        distance = result.get("distance", 0)
        similarity = 1 - distance if distance else 0

        console.print(f"\n[bold]Result {i}[/bold] (similarity: {similarity:.2%})")
        console.print(f"[blue]Question:[/blue] {meta.get('question', '')}")
        console.print(f"[green]SQL:[/green] {meta.get('sql_query', '')}")


@app.command("delete")
def delete_sql_pair(
    pair_id: str = typer.Argument(..., help="ID of the SQL pair to delete"),
):
    """Delete a SQL pair by ID."""
    vector_store = get_vector_store_service()
    vector_store.delete_sql_pair(pair_id)
    console.print(f"[green]Deleted SQL pair: {pair_id}[/green]")


@app.command("clear")
def clear_sql_pairs(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear all SQL pairs from the vector store."""
    if not confirm:
        confirm = typer.confirm("Are you sure you want to delete all SQL pairs?")

    if confirm:
        vector_store = get_vector_store_service()
        vector_store.clear_collection("sql_pairs")
        console.print("[green]Cleared all SQL pairs[/green]")
    else:
        console.print("[yellow]Cancelled[/yellow]")
