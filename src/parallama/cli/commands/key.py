"""CLI commands for managing API keys."""

from datetime import datetime, timezone, timedelta
from typing import Optional
from uuid import UUID

import typer
from sqlalchemy.orm import Session

from ...services.api_key import APIKeyService
from ...core.database import get_db, get_redis
from ..output import print_error, print_success, print_key, print_table
from rich.table import Table

key_cli = typer.Typer(help="Manage API keys")

@key_cli.command("create")
def create_key(
    user_id: UUID = typer.Argument(..., help="User ID to create key for"),
    name: str = typer.Option(None, help="Name for the API key"),
    expires_in: Optional[int] = typer.Option(
        None,
        help="Key expiry in days (default: never expires)"
    )
):
    """Create a new API key."""
    try:
        # Get services
        db = next(get_db())
        redis = next(get_redis())
        api_key_service = APIKeyService(db, redis)

        # Create key
        expires_at = None
        if expires_in:
            expires_at = datetime.now(timezone.utc).replace(
                hour=23, minute=59, second=59
            ) + timedelta(days=expires_in)

        key = api_key_service.create_key(
            user_id=str(user_id),
            name=name,
            expires_at=expires_at
        )

        # Print key
        print_key(key.key)
        print_success("API key created successfully")

    except Exception as e:
        print_error(str(e))
    finally:
        db.close()
        redis.close()

@key_cli.command("list")
def list_keys(
    user_id: Optional[UUID] = typer.Option(
        None,
        help="Filter keys by user ID"
    ),
    show_expired: bool = typer.Option(
        False,
        help="Include expired keys"
    )
):
    """List API keys."""
    try:
        # Get services
        db = next(get_db())
        redis = next(get_redis())
        api_key_service = APIKeyService(db, redis)

        # Get keys
        keys = api_key_service.list_keys(
            user_id=str(user_id) if user_id else None,
            include_expired=show_expired
        )

        # Create table
        table = Table("ID", "Name", "User ID", "Created", "Expires", "Last Used")
        for key in keys:
            table.add_row(
                key.id,
                key.name or "",
                key.user_id,
                key.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                key.expires_at.strftime("%Y-%m-%d %H:%M:%S") if key.expires_at else "Never",
                key.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if key.last_used_at else "Never"
            )

        print_table(table)

    except Exception as e:
        print_error(str(e))
    finally:
        db.close()
        redis.close()

@key_cli.command("revoke")
def revoke_key(
    key_id: UUID = typer.Argument(..., help="ID of key to revoke")
):
    """Revoke an API key."""
    try:
        # Get services
        db = next(get_db())
        redis = next(get_redis())
        api_key_service = APIKeyService(db, redis)

        # Revoke key
        api_key_service.revoke_key(str(key_id))
        print_success(f"API key {key_id} revoked successfully")

    except Exception as e:
        print_error(str(e))
    finally:
        db.close()
        redis.close()

@key_cli.command("revoke-all")
def revoke_all_keys(
    user_id: UUID = typer.Argument(..., help="User ID to revoke keys for")
):
    """Revoke all API keys for a user."""
    try:
        # Get services
        db = next(get_db())
        redis = next(get_redis())
        api_key_service = APIKeyService(db, redis)

        # Revoke keys
        api_key_service.revoke_all_user_keys(str(user_id))
        print_success(f"All API keys for user {user_id} revoked successfully")

    except Exception as e:
        print_error(str(e))
    finally:
        db.close()
        redis.close()

@key_cli.command("info")
def get_key_info(
    key_id: UUID = typer.Argument(..., help="ID of key to get info for")
):
    """Get information about an API key."""
    try:
        # Get services
        db = next(get_db())
        redis = next(get_redis())
        api_key_service = APIKeyService(db, redis)

        # Get key
        key = api_key_service.get_key(str(key_id))
        if not key:
            print_error(f"API key {key_id} not found")
            return

        # Create table
        table = Table("Field", "Value")
        table.add_row("ID", key.id)
        table.add_row("Name", key.name or "")
        table.add_row("User ID", key.user_id)
        table.add_row("Created", key.created_at.strftime("%Y-%m-%d %H:%M:%S"))
        table.add_row(
            "Expires",
            key.expires_at.strftime("%Y-%m-%d %H:%M:%S") if key.expires_at else "Never"
        )
        table.add_row(
            "Last Used",
            key.last_used_at.strftime("%Y-%m-%d %H:%M:%S") if key.last_used_at else "Never"
        )
        table.add_row("Is Valid", str(not key.is_revoked()))

        print_table(table)

    except Exception as e:
        print_error(str(e))
    finally:
        db.close()
        redis.close()
