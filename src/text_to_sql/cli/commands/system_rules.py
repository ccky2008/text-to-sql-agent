"""System rules CLI commands."""

from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from text_to_sql.services.system_rules import get_system_rules_service

app = typer.Typer(help="View system rules configuration")
console = Console()


@app.command("show")
def show_rules(
    raw: bool = typer.Option(False, "--raw", "-r", help="Show raw JSON"),
):
    """Display current system rules."""
    rules_service = get_system_rules_service()

    if raw:
        import json

        syntax = Syntax(
            json.dumps(rules_service.rules, indent=2),
            "json",
            theme="monokai",
            line_numbers=True,
        )
        console.print(syntax)
    else:
        formatted = rules_service.format_for_prompt()
        if formatted:
            console.print(Panel(formatted, title="System Rules", border_style="blue"))
        else:
            console.print("[yellow]No system rules configured[/yellow]")


@app.command("path")
def show_path():
    """Show the path to the system rules file."""
    rules_service = get_system_rules_service()
    path = rules_service._rules_path
    exists = path.exists()

    console.print(f"[blue]Rules file:[/blue] {path}")
    if exists:
        console.print("[green]Status: File exists[/green]")
    else:
        console.print("[yellow]Status: File not found[/yellow]")
