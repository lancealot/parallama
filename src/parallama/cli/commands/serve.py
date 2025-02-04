"""CLI command for serving the API."""

import typer
import uvicorn
from typing import Optional

from ...api.app import app
from ...core.config import settings

serve_cli = typer.Typer(help="Serve the API")

@serve_cli.command("start")
def start_server(
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        "-h",
        help="Host to bind to"
    ),
    port: int = typer.Option(
        8000,
        "--port",
        "-p",
        help="Port to bind to"
    ),
    workers: int = typer.Option(
        4,
        "--workers",
        "-w",
        help="Number of worker processes"
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload"
    ),
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file"
    )
):
    """Start the API server."""
    uvicorn.run(
        "parallama.api.app:app",
        host=host,
        port=port,
        workers=workers,
        reload=reload,
        log_level=settings.logging.level.lower(),
        proxy_headers=True,
        forwarded_allow_ips="*"
    )
