from __future__ import annotations

from pathlib import Path

import typer
import uvicorn
from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

from api.config import settings

app = typer.Typer(
    name="api",
    help="Invoice Processing Engine API CLI",
    no_args_is_help=True,
)


_ALEMBIC_INI_PATH = Path(__file__).resolve().parents[2] / "alembic.ini"


def _alembic_config() -> AlembicConfig:
    config = AlembicConfig(str(_ALEMBIC_INI_PATH))
    config.set_main_option("script_location", str(_ALEMBIC_INI_PATH.parent / "alembic"))
    return config


@app.command()
def serve(
    host: str = typer.Option(settings.api_host, "--host", "-h", help="Bind host"),
    port: int = typer.Option(settings.api_port, "--port", "-p", help="Bind port"),
    workers: int = typer.Option(1, "--workers", "-w", help="Number of worker processes"),
):
    """Start the production API server."""
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        workers=workers,
        log_level="info",
    )


@app.command()
def dev(
    host: str = typer.Option("127.0.0.1", "--host", "-h", help="Bind host"),
    port: int = typer.Option(settings.api_port, "--port", "-p", help="Bind port"),
):
    """Start the development API server with hot-reload."""
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        reload=True,
        log_level="debug",
    )


@app.command()
def migrate(
    revision: str = typer.Argument("head", help="Target Alembic revision (default: head)"),
):
    """Apply Alembic database migrations."""
    alembic_command.upgrade(_alembic_config(), revision)


@app.command()
def downgrade(
    revision: str = typer.Argument("-1", help="Target Alembic revision (default: previous)"),
):
    """Roll back Alembic database migrations."""
    alembic_command.downgrade(_alembic_config(), revision)
