"""Parallama CLI - Multi-user authentication for Ollama."""
import click
from .commands.user import user_cli
from .commands.key import key_cli
from .commands.ratelimit import ratelimit_cli
from .commands.usage import usage_cli
from .core.db import init_db, cleanup_db

@click.group()
def cli():
    """Parallama CLI - Multi-user authentication and access management for Ollama."""
    pass

@cli.result_callback()
def cleanup(result, **kwargs):
    """Cleanup database connections after command execution."""
    cleanup_db()

# Register command groups
cli.add_command(user_cli)
cli.add_command(key_cli)
cli.add_command(ratelimit_cli)
cli.add_command(usage_cli)

def main():
    """Main entry point for the CLI."""
    init_db()
    cli(auto_envvar_prefix='PARALLAMA')

if __name__ == '__main__':
    main()
