"""CLI module."""
import typer

from text_to_sql.cli.commands import database_info, metadata, sql_pairs, system_rules

app = typer.Typer(help="Text-to-SQL Agent CLI")
app.add_typer(sql_pairs.app, name="sql-pairs")
app.add_typer(metadata.app, name="metadata")
app.add_typer(database_info.app, name="database-info")
app.add_typer(system_rules.app, name="system-rules")
