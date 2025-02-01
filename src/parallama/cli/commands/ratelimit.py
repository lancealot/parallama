"""Rate limit management commands."""
import click
from typing import Optional
from datetime import datetime

from parallama.models.user import User
from parallama.models.rate_limit import GatewayRateLimit
from parallama.core.exceptions import ResourceNotFoundError

from ..core.db import get_db, get_redis
from ..utils.output import (
    print_error,
    print_success,
    print_table,
    format_dict,
    confirm_action
)

@click.group(name='ratelimit')
def ratelimit_cli():
    """Rate limit management commands."""
    pass

@ratelimit_cli.command(name='set')
@click.argument('username')
@click.argument('gateway_type')
@click.option('--token-hourly', type=int, help='Hourly token limit')
@click.option('--token-daily', type=int, help='Daily token limit')
@click.option('--request-hourly', type=int, help='Hourly request limit')
@click.option('--request-daily', type=int, help='Daily request limit')
def set_rate_limit(
    username: str,
    gateway_type: str,
    token_hourly: Optional[int],
    token_daily: Optional[int],
    request_hourly: Optional[int],
    request_daily: Optional[int]
):
    """Set rate limits for a user and gateway."""
    if not any([token_hourly, token_daily, request_hourly, request_daily]):
        print_error("No rate limits specified")
        raise click.Abort()
    
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Find or create rate limit
        rate_limit = db.query(GatewayRateLimit).filter(
            GatewayRateLimit.user_id == user.id,
            GatewayRateLimit.gateway_type == gateway_type
        ).first()
        
        if not rate_limit:
            rate_limit = GatewayRateLimit(
                user_id=user.id,
                gateway_type=gateway_type
            )
            db.add(rate_limit)
        
        # Prepare changes
        changes = []
        if token_hourly is not None:
            changes.append(f"hourly token limit to {token_hourly}")
            rate_limit.token_limit_hourly = token_hourly
        if token_daily is not None:
            changes.append(f"daily token limit to {token_daily}")
            rate_limit.token_limit_daily = token_daily
        if request_hourly is not None:
            changes.append(f"hourly request limit to {request_hourly}")
            rate_limit.request_limit_hourly = request_hourly
        if request_daily is not None:
            changes.append(f"daily request limit to {request_daily}")
            rate_limit.request_limit_daily = request_daily
        
        # Confirm action
        message = f"Set rate limits for user '{username}' on gateway '{gateway_type}' - {', '.join(changes)}?"
        confirm_action(message)
        
        # Update timestamp
        rate_limit.updated_at = datetime.utcnow()
        
        # Save changes
        db.commit()
        
        print_success(f"Rate limits updated for user '{username}' on gateway '{gateway_type}'")
        
        # Show updated limits
        limits = {
            'Gateway': gateway_type,
            'Token Limit (Hourly)': rate_limit.token_limit_hourly or 'Not set',
            'Token Limit (Daily)': rate_limit.token_limit_daily or 'Not set',
            'Request Limit (Hourly)': rate_limit.request_limit_hourly or 'Not set',
            'Request Limit (Daily)': rate_limit.request_limit_daily or 'Not set',
            'Updated': rate_limit.updated_at
        }
        format_dict(limits, "Rate Limits")
        
    except Exception as e:
        db.rollback()
        print_error(f"Failed to set rate limits: {str(e)}")
        raise click.Abort()

@ratelimit_cli.command(name='get')
@click.argument('username')
@click.argument('gateway_type', required=False)
def get_rate_limits(username: str, gateway_type: Optional[str]):
    """Get rate limits for a user."""
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Query rate limits
        query = db.query(GatewayRateLimit).filter(GatewayRateLimit.user_id == user.id)
        if gateway_type:
            query = query.filter(GatewayRateLimit.gateway_type == gateway_type)
        rate_limits = query.all()
        
        if not rate_limits:
            print_error(f"No rate limits found for user '{username}'" + 
                       (f" on gateway '{gateway_type}'" if gateway_type else ""))
            raise click.Abort()
        
        # Prepare table data
        headers = ['Gateway', 'Token/Hour', 'Token/Day', 'Req/Hour', 'Req/Day', 'Updated']
        rows = [
            [
                rl.gateway_type,
                rl.token_limit_hourly or 'Not set',
                rl.token_limit_daily or 'Not set',
                rl.request_limit_hourly or 'Not set',
                rl.request_limit_daily or 'Not set',
                rl.updated_at
            ]
            for rl in rate_limits
        ]
        
        print_table(headers, rows, f"Rate Limits for {username}")
        
    except Exception as e:
        print_error(f"Failed to get rate limits: {str(e)}")
        raise click.Abort()

@ratelimit_cli.command(name='reset')
@click.argument('username')
@click.argument('gateway_type')
def reset_rate_limits(username: str, gateway_type: str):
    """Reset rate limits to defaults for a user and gateway."""
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Find rate limit
        rate_limit = db.query(GatewayRateLimit).filter(
            GatewayRateLimit.user_id == user.id,
            GatewayRateLimit.gateway_type == gateway_type
        ).first()
        
        if not rate_limit:
            print_error(f"No rate limits found for user '{username}' on gateway '{gateway_type}'")
            raise click.Abort()
        
        # Confirm reset
        confirm_action(f"Reset rate limits for user '{username}' on gateway '{gateway_type}'?")
        
        # Delete rate limit (system will use defaults)
        db.delete(rate_limit)
        db.commit()
        
        print_success(f"Rate limits reset for user '{username}' on gateway '{gateway_type}'")
        
    except Exception as e:
        db.rollback()
        print_error(f"Failed to reset rate limits: {str(e)}")
        raise click.Abort()
