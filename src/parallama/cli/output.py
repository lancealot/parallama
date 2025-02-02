"""CLI output utilities."""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table

console = Console()

def print_error(message: str) -> None:
    """Print error message in red.
    
    Args:
        message: Error message to print
    """
    console.print(f"Error: {message}", style="red")

def print_success(message: str) -> None:
    """Print success message in green.
    
    Args:
        message: Success message to print
    """
    console.print(message, style="green")

def print_warning(message: str) -> None:
    """Print warning message in yellow.
    
    Args:
        message: Warning message to print
    """
    console.print(f"Warning: {message}", style="yellow")

def print_key(key: str) -> None:
    """Print API key with special formatting.
    
    Args:
        key: API key to print
    """
    console.print("\nAPI Key:", style="bold")
    console.print(key, style="green")
    console.print("\nStore this key securely - it won't be shown again.\n")

def print_table(table: Table) -> None:
    """Print rich table.
    
    Args:
        table: Rich table to print
    """
    console.print(table)

def format_dict(data: Dict[str, Any], key_width: Optional[int] = None) -> str:
    """Format dictionary for display.
    
    Args:
        data: Dictionary to format
        key_width: Optional fixed width for keys
        
    Returns:
        str: Formatted string
    """
    if not data:
        return "None"
    
    # Find max key length if width not specified
    if key_width is None:
        key_width = max(len(str(k)) for k in data.keys())
    
    # Format each line
    lines = []
    for key, value in data.items():
        key_str = str(key).ljust(key_width)
        if isinstance(value, dict):
            # Handle nested dictionaries
            nested = format_dict(value, key_width)
            lines.append(f"{key_str}: {nested}")
        else:
            lines.append(f"{key_str}: {value}")
    
    return "\n".join(lines)

def confirm_action(message: str) -> bool:
    """Prompt user to confirm an action.
    
    Args:
        message: Confirmation message
        
    Returns:
        bool: True if confirmed, False otherwise
    """
    response = console.input(f"{message} [y/N] ")
    return response.lower() == "y"
