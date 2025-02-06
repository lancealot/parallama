"""CLI application."""

import os
from pathlib import Path
import click
from typing import Optional

from ..core.config import load_settings
from .commands.user import user_cli
from .commands.key import key_cli
from .commands.ratelimit import ratelimit_cli
from .commands.usage import usage_cli
from .commands.serve import serve_cli

@click.group()
@click.option(
    "--config",
    "-c",
    help="Path to config file",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
)
@click.option("--debug", is_flag=True, help="Enable debug mode")
def cli(config: Optional[Path], debug: bool) -> None:
    """Parallama CLI."""
    if config:
        load_settings(config)
    else:
        # Try default locations
        default_paths = [
            Path("/etc/parallama/config.yaml"),
            Path(os.path.expanduser("~/.config/parallama/config.yaml")),
            Path("config.yaml"),
        ]
        for path in default_paths:
            if path.exists():
                load_settings(path)
                break

# Register commands
cli.add_command(user_cli, "user")
cli.add_command(key_cli, "key")
cli.add_command(ratelimit_cli, "ratelimit")
cli.add_command(usage_cli, "usage")
cli.add_command(serve_cli, "serve")

def main():
    """Entry point for the CLI."""
    cli()

if __name__ == "__main__":
    main()
