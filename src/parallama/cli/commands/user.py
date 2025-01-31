"""User management commands."""
import click
from uuid import UUID
from typing import Optional

from parallama.models.user import User
from parallama.services.auth import AuthService
from parallama.services.role import RoleService
from parallama.core.exceptions import ResourceNotFoundError, DuplicateResourceError

from ..core.db import get_db, get_redis
from ..utils.output import (
    print_error,
    print_success,
    print_table,
    format_dict,
    confirm_action
)

@click.group(name='user')
def user_cli():
    """User management commands."""
    pass

@user_cli.command(name='create')
@click.argument('username')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True)
@click.option('--role', type=click.Choice(['basic', 'premium']), default='basic')
@click.option('--admin', is_flag=True, help='Create as admin user')
def create_user(username: str, password: str, role: str, admin: bool):
    """Create a new user."""
    db = get_db()
    redis = get_redis()
    
    try:
        # Create user
        user = User(
            username=username,
            role=role,
            is_admin=admin
        )
        user.set_password(password)
        
        # Add to database
        db.add(user)
        db.commit()
        
        # Initialize roles
        role_service = RoleService(db)
        role_service.initialize_default_roles()  # Ensure roles exist
        role_model = role_service.get_role_by_name(role)
        if role_model:
            role_service.assign_role_to_user(user.id, role_model.id)
        
        print_success(f"User '{username}' created successfully")
        
        # Show user details
        user_info = {
            'Username': user.username,
            'Role': user.role,
            'Admin': 'Yes' if user.is_admin else 'No',
            'Created': user.created_at
        }
        format_dict(user_info, "User Details")
        
    except DuplicateResourceError:
        print_error(f"User '{username}' already exists")
        raise click.Abort()
    except Exception as e:
        db.rollback()
        print_error(f"Failed to create user: {str(e)}")
        raise click.Abort()

@user_cli.command(name='list')
@click.option('--role', help='Filter by role')
def list_users(role: Optional[str]):
    """List all users."""
    db = get_db()
    
    try:
        # Query users
        query = db.query(User)
        if role:
            query = query.filter(User.role == role)
        users = query.all()
        
        # Prepare table data
        headers = ['Username', 'Role', 'Admin', 'Created']
        rows = [
            [u.username, u.role, 'Yes' if u.is_admin else 'No', u.created_at]
            for u in users
        ]
        
        print_table(headers, rows, "Users")
        
    except Exception as e:
        print_error(f"Failed to list users: {str(e)}")
        raise click.Abort()

@user_cli.command(name='info')
@click.argument('username')
def get_user_info(username: str):
    """Get detailed information about a user."""
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Get user roles
        role_service = RoleService(db)
        roles = role_service.get_user_roles(user.id)
        role_names = [r.name for r in roles]
        
        # Show user details
        user_info = {
            'Username': user.username,
            'Role': user.role,
            'Admin': 'Yes' if user.is_admin else 'No',
            'Created': user.created_at,
            'Roles': ', '.join(role_names) if role_names else 'None'
        }
        format_dict(user_info, "User Details")
        
    except Exception as e:
        print_error(f"Failed to get user info: {str(e)}")
        raise click.Abort()

@user_cli.command(name='update')
@click.argument('username')
@click.option('--role', type=click.Choice(['basic', 'premium']))
@click.option('--admin/--no-admin', help='Toggle admin status')
def update_user(username: str, role: Optional[str], admin: Optional[bool]):
    """Update user details."""
    if not any([role, admin is not None]):
        print_error("No updates specified")
        raise click.Abort()
    
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Confirm action
        changes = []
        if role and role != user.role:
            changes.append(f"role from '{user.role}' to '{role}'")
        if admin is not None and admin != user.is_admin:
            changes.append(f"admin status to {'enabled' if admin else 'disabled'}")
        
        if changes:
            message = f"Update user '{username}' - change {' and '.join(changes)}?"
            confirm_action(message)
            
            # Apply updates
            if role:
                user.role = role
                # Update role assignment
                role_service = RoleService(db)
                role_model = role_service.get_role_by_name(role)
                if role_model:
                    # Remove existing roles
                    for old_role in role_service.get_user_roles(user.id):
                        role_service.remove_role_from_user(user.id, old_role.id)
                    # Assign new role
                    role_service.assign_role_to_user(user.id, role_model.id)
            
            if admin is not None:
                user.is_admin = admin
            
            db.commit()
            print_success(f"User '{username}' updated successfully")
            
            # Show updated user details
            user_info = {
                'Username': user.username,
                'Role': user.role,
                'Admin': 'Yes' if user.is_admin else 'No',
                'Updated': user.updated_at
            }
            format_dict(user_info, "Updated User Details")
        
    except Exception as e:
        db.rollback()
        print_error(f"Failed to update user: {str(e)}")
        raise click.Abort()

@user_cli.command(name='delete')
@click.argument('username')
def delete_user(username: str):
    """Delete a user."""
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Confirm deletion
        confirm_action(f"Delete user '{username}'? This action cannot be undone!")
        
        # Delete user
        db.delete(user)
        db.commit()
        
        print_success(f"User '{username}' deleted successfully")
        
    except Exception as e:
        db.rollback()
        print_error(f"Failed to delete user: {str(e)}")
        raise click.Abort()
