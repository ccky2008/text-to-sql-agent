"""Metadata CLI commands."""

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from text_to_sql.core.types import MetadataCategory
from text_to_sql.models.data_sources import MetadataEntry
from text_to_sql.services.vector_store import get_vector_store_service

app = typer.Typer(help="Manage domain metadata for business context")
console = Console()


@app.command("add")
def add_metadata(
    title: str = typer.Option(..., "-t", "--title", help="Title of the metadata entry"),
    content: str = typer.Option(..., "-c", "--content", help="Content/description"),
    category: str = typer.Option(
        ...,
        "--category",
        help="Category: business_rule, domain_term, or context",
    ),
    related_tables: str = typer.Option("", "--tables", help="Comma-separated related tables"),
    keywords: str = typer.Option("", "-k", "--keywords", help="Comma-separated keywords"),
):
    """Add a new metadata entry to the vector store."""
    try:
        cat = MetadataCategory(category.lower())
    except ValueError:
        console.print(
            f"[red]Invalid category: {category}. "
            "Use business_rule/domain_term/context[/red]"
        )
        raise typer.Exit(1)

    entry = MetadataEntry(
        title=title,
        content=content,
        category=cat,
        related_tables=[t.strip() for t in related_tables.split(",") if t.strip()],
        keywords=[k.strip() for k in keywords.split(",") if k.strip()],
    )

    vector_store = get_vector_store_service()
    entry_id, is_update = vector_store.add_metadata(entry)

    if is_update:
        console.print(f"[cyan]Updated metadata with ID: {entry_id}[/cyan]")
    else:
        console.print(f"[green]Added metadata with ID: {entry_id}[/green]")


@app.command("import")
def import_metadata(
    file_path: Path = typer.Argument(..., help="Path to JSON file with metadata entries"),
):
    """Import metadata entries from a JSON file.

    Expected format:
    [
        {
            "title": "...",
            "content": "...",
            "category": "business_rule",
            "related_tables": ["table1"],
            "keywords": ["keyword1"]
        }
    ]
    """
    if not file_path.exists():
        console.print(f"[red]File not found: {file_path}[/red]")
        raise typer.Exit(1)

    with open(file_path) as f:
        data = json.load(f)

    if not isinstance(data, list):
        console.print("[red]JSON must be an array of metadata objects[/red]")
        raise typer.Exit(1)

    vector_store = get_vector_store_service()
    added_count = 0
    updated_count = 0
    error_count = 0

    for item in data:
        try:
            category = MetadataCategory(item.get("category", "context").lower())
            entry = MetadataEntry(
                title=item["title"],
                content=item["content"],
                category=category,
                related_tables=item.get("related_tables", []),
                keywords=item.get("keywords", []),
            )
            _, is_update = vector_store.add_metadata(entry)
            if is_update:
                updated_count += 1
            else:
                added_count += 1
        except Exception as e:
            console.print(f"[yellow]Error importing entry: {e}[/yellow]")
            error_count += 1

    console.print(f"[green]Added {added_count} entries, updated {updated_count} entries[/green]")
    if error_count:
        console.print(f"[yellow]Failed to import {error_count} entries[/yellow]")


@app.command("list")
def list_metadata(
    limit: int = typer.Option(20, "-n", "--limit", help="Number of entries to show"),
    offset: int = typer.Option(0, "--offset", help="Offset for pagination"),
):
    """List all metadata entries in the vector store."""
    vector_store = get_vector_store_service()
    entries = vector_store.list_metadata(limit=limit, offset=offset)
    total = vector_store.get_metadata_count()

    if not entries:
        console.print("[yellow]No metadata entries found[/yellow]")
        return

    table = Table(title=f"Metadata Entries ({len(entries)} of {total})")
    table.add_column("ID", style="dim", max_width=8)
    table.add_column("Title", max_width=30)
    table.add_column("Category")
    table.add_column("Content", max_width=40)

    for entry in entries:
        meta = entry.get("metadata", {})
        table.add_row(
            meta.get("id", "")[:8],
            meta.get("title", "")[:30],
            meta.get("category", ""),
            meta.get("content", "")[:40],
        )

    console.print(table)


@app.command("search")
def search_metadata(
    query: str = typer.Argument(..., help="Search query"),
    category: str = typer.Option(None, "--category", help="Filter by category"),
    n_results: int = typer.Option(5, "-n", help="Number of results"),
):
    """Search for relevant metadata entries."""
    vector_store = get_vector_store_service()
    results = vector_store.search_metadata(query, n_results=n_results, category=category)

    if not results:
        console.print("[yellow]No matching metadata found[/yellow]")
        return

    for i, result in enumerate(results, 1):
        meta = result.get("metadata", {})
        distance = result.get("distance", 0)
        similarity = 1 - distance if distance else 0

        console.print(f"\n[bold]Result {i}[/bold] (similarity: {similarity:.2%})")
        console.print(f"[blue]Title:[/blue] {meta.get('title', '')}")
        console.print(f"[dim]Category:[/dim] {meta.get('category', '')}")
        console.print(f"[green]Content:[/green] {meta.get('content', '')}")


@app.command("delete")
def delete_metadata(
    entry_id: str = typer.Argument(..., help="ID of the metadata entry to delete"),
):
    """Delete a metadata entry by ID."""
    vector_store = get_vector_store_service()
    vector_store.delete_metadata(entry_id)
    console.print(f"[green]Deleted metadata entry: {entry_id}[/green]")


@app.command("clear")
def clear_metadata(
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation"),
):
    """Clear all metadata from the vector store."""
    if not confirm:
        confirm = typer.confirm("Are you sure you want to delete all metadata?")

    if confirm:
        vector_store = get_vector_store_service()
        vector_store.clear_collection("domain_metadata")
        console.print("[green]Cleared all metadata[/green]")
    else:
        console.print("[yellow]Cancelled[/yellow]")
