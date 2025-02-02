"""CLI application."""

import typer
from typing import Optional

from .commands.user import user_cli
from .commands.key import key_cli
from .commands.ratelimit import ratelimit_cli
from .commands.usage import usage_cli

# Create main CLI app
cli = typer.Typer(help="Parallama CLI")

# Register commands
cli.add_typer(user_cli, name="user", help="Manage users")
cli.add_typer(key_cli, name="key", help="Manage API keys")
cli.add_typer(ratelimit_cli, name="ratelimit", help="Manage rate limits")
cli.add_typer(usage_cli, name="usage", help="View usage statistics")

@cli.callback()
def callback(
    config: Optional[str] = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to config file"
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug mode"
    )
) -> None:
    """Parallama CLI."""
    pass

if __name__ == "__main__":
    cli()
