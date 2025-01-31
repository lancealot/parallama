"""Output formatting utilities for CLI commands."""
import sys
from typing import List, Dict, Any
from datetime import datetime
import click
from tabulate import tabulate

def format_datetime(dt: datetime) -> str:
    """Format a datetime object for display."""
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def print_error(message: str) -> None:
    """Print an error message in red."""
    click.secho(f"Error: {message}", fg="red", err=True)

def print_success(message: str) -> None:
    """Print a success message in green."""
    click.secho(message, fg="green")

def print_warning(message: str) -> None:
    """Print a warning message in yellow."""
    click.secho(f"Warning: {message}", fg="yellow")

def print_table(headers: List[str], rows: List[List[Any]], title: str = None) -> None:
    """Print data in a formatted table."""
    if title:
        click.secho(f"\n{title}", fg="blue", bold=True)
    
    if not rows:
        click.secho("No data available", fg="yellow")
        return
    
    # Format any datetime objects
    formatted_rows = []
    for row in rows:
        formatted_row = []
        for cell in row:
            if isinstance(cell, datetime):
                formatted_row.append(format_datetime(cell))
            else:
                formatted_row.append(str(cell) if cell is not None else "N/A")
        formatted_rows.append(formatted_row)
    
    click.echo(tabulate(
        formatted_rows,
        headers=headers,
        tablefmt="grid"
    ))

def print_key(key: str, description: str = None) -> None:
    """Print an API key with optional description."""
    click.secho("\nAPI Key:", fg="blue", bold=True)
    click.echo(key)
    if description:
        click.echo(f"Description: {description}")
    click.echo("\nStore this key securely - it won't be shown again!")

def confirm_action(message: str, abort: bool = True) -> bool:
    """
    Prompt for confirmation before proceeding with an action.
    
    Args:
        message: The confirmation message to display
        abort: Whether to abort if the user doesn't confirm
    
    Returns:
        bool: True if confirmed, False if not confirmed
    """
    try:
        return click.confirm(message, abort=abort)
    except click.Abort:
        click.echo("\nOperation cancelled.")
        sys.exit(1)

def format_dict(data: Dict[str, Any], title: str = None) -> None:
    """Print a dictionary in a formatted way."""
    if title:
        click.secho(f"\n{title}", fg="blue", bold=True)
    
    if not data:
        click.secho("No data available", fg="yellow")
        return
    
    max_key_length = max(len(str(k)) for k in data.keys())
    
    for key, value in data.items():
        if isinstance(value, datetime):
            value = format_datetime(value)
        elif value is None:
            value = "N/A"
        
        # Create a padded key string with exact width
        padded_key = f"{str(key):<{max_key_length}}"
        key_str = click.style(padded_key, fg="cyan")
        click.echo(f"{key_str}: {value}")
