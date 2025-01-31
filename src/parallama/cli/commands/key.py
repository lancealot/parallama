"""API key management commands."""
import click
from uuid import UUID
from typing import Optional

from parallama.models.user import User
from parallama.models.api_key import APIKey
from parallama.services.api_key import APIKeyService
from parallama.core.exceptions import ResourceNotFoundError

from ..core.db import get_db, get_redis
from ..utils.output import (
    print_error,
    print_success,
    print_table,
    print_key,
    confirm_action
)

@click.group(name='key')
def key_cli():
    """API key management commands."""
    pass

@key_cli.command(name='generate')
@click.argument('username')
@click.option('--description', help='Description of the API key')
def generate_key(username: str, description: Optional[str]):
    """Generate a new API key for a user."""
    db = get_db()
    redis = get_redis()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Create API key
        api_key_service = APIKeyService(db, redis)
        key = api_key_service.create_key(user.id, description)
        
        print_success(f"API key generated for user '{username}'")
        print_key(key, description)
        
    except Exception as e:
        db.rollback()
        print_error(f"Failed to generate API key: {str(e)}")
        raise click.Abort()

@key_cli.command(name='list')
@click.option('--username', required=True, help='Username to list keys for')
def list_keys(username: str):
    """List API keys for a user."""
    db = get_db()
    redis = get_redis()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Get API keys
        api_key_service = APIKeyService(db, redis)
        keys = api_key_service.list_keys(user.id)
        
        # Prepare table data
        headers = ['ID', 'Description', 'Created', 'Last Used', 'Status']
        rows = [
            [
                str(k['id']),
                k['description'] or 'N/A',
                k['created_at'],
                k['last_used_at'],
                'Revoked' if k['revoked_at'] else 'Active'
            ]
            for k in keys
        ]
        
        print_table(headers, rows, f"API Keys for {username}")
        
    except Exception as e:
        print_error(f"Failed to list API keys: {str(e)}")
        raise click.Abort()

@key_cli.command(name='revoke')
@click.argument('key-id')
def revoke_key(key_id: str):
    """Revoke an API key."""
    db = get_db()
    redis = get_redis()
    
    try:
        # Find API key
        key = db.query(APIKey).filter(APIKey.id == key_id).first()
        if not key:
            print_error(f"API key '{key_id}' not found")
            raise click.Abort()
        
        # Get user info for confirmation
        user = db.query(User).filter(User.id == key.user_id).first()
        
        # Confirm revocation
        message = (
            f"Revoke API key for user '{user.username}'?\n"
            f"Description: {key.description or 'N/A'}\n"
            "This action cannot be undone!"
        )
        confirm_action(message)
        
        # Revoke key
        api_key_service = APIKeyService(db, redis)
        api_key_service.revoke_key(key_id)
        
        print_success("API key revoked successfully")
        
    except ValueError:
        print_error("Invalid key ID format")
        raise click.Abort()
    except Exception as e:
        db.rollback()
        print_error(f"Failed to revoke API key: {str(e)}")
        raise click.Abort()
