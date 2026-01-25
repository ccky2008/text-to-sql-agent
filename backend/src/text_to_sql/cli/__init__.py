"""CLI module."""
import typer
import uvicorn

from text_to_sql.cli.commands import database_info, metadata, sql_pairs, system_rules
from text_to_sql.config.settings import get_settings

app = typer.Typer(help="Text-to-SQL Agent CLI")
app.add_typer(sql_pairs.app, name="sql-pairs")
app.add_typer(metadata.app, name="metadata")
app.add_typer(database_info.app, name="database-info")
app.add_typer(system_rules.app, name="system-rules")


@app.command()
def serve():
    """Run the API server with uvicorn."""
    s = get_settings()
    uvicorn.run(
        "text_to_sql.main:app",
        host=s.api_host,
        port=s.api_port,
        reload=s.api_debug,
    )
