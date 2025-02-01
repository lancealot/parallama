"""Usage reporting commands."""
import click
import json
import csv
from typing import Optional
from datetime import datetime, timedelta
from io import StringIO

from parallama.models.user import User
from parallama.models.rate_limit import GatewayUsageLog
from parallama.core.exceptions import ResourceNotFoundError

from ..core.db import get_db
from ..utils.output import (
    print_error,
    print_success,
    print_table,
    format_dict,
    confirm_action
)

@click.group(name='usage')
def usage_cli():
    """Usage reporting commands."""
    pass

@usage_cli.command(name='list')
@click.argument('username')
@click.option('--gateway', help='Filter by gateway type')
@click.option('--days', type=int, default=7, help='Number of days to show (default: 7)')
@click.option('--model', help='Filter by model name')
def list_usage(username: str, gateway: Optional[str], days: int, model: Optional[str]):
    """List usage history for a user."""
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query usage logs
        query = db.query(GatewayUsageLog).filter(
            GatewayUsageLog.user_id == user.id,
            GatewayUsageLog.timestamp >= start_date
        )
        if gateway:
            query = query.filter(GatewayUsageLog.gateway_type == gateway)
        if model:
            query = query.filter(GatewayUsageLog.model_name == model)
        
        logs = query.order_by(GatewayUsageLog.timestamp.desc()).all()
        
        if not logs:
            print_error(f"No usage logs found for the specified criteria")
            raise click.Abort()
        
        # Prepare table data
        headers = ['Timestamp', 'Gateway', 'Model', 'Tokens', 'Duration (ms)', 'Status']
        rows = [
            [
                log.timestamp,
                log.gateway_type,
                log.model_name or 'N/A',
                log.tokens_used or 0,
                log.request_duration or 0,
                log.status_code
            ]
            for log in logs
        ]
        
        print_table(headers, rows, f"Usage History for {username}")
        
    except Exception as e:
        print_error(f"Failed to list usage: {str(e)}")
        raise click.Abort()

@usage_cli.command(name='summary')
@click.argument('username')
@click.option('--gateway', help='Filter by gateway type')
@click.option('--days', type=int, default=30, help='Number of days to analyze (default: 30)')
@click.option('--model', help='Filter by model name')
def usage_summary(username: str, gateway: Optional[str], days: int, model: Optional[str]):
    """Display aggregated usage statistics."""
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query usage logs
        query = db.query(GatewayUsageLog).filter(
            GatewayUsageLog.user_id == user.id,
            GatewayUsageLog.timestamp >= start_date
        )
        if gateway:
            query = query.filter(GatewayUsageLog.gateway_type == gateway)
        if model:
            query = query.filter(GatewayUsageLog.model_name == model)
        
        logs = query.all()
        
        if not logs:
            print_error(f"No usage logs found for the specified criteria")
            raise click.Abort()
        
        # Calculate statistics
        total_requests = len(logs)
        total_tokens = sum(log.tokens_used or 0 for log in logs)
        total_duration = sum(log.request_duration or 0 for log in logs)
        success_requests = len([log for log in logs if log.status_code == 200])
        error_requests = total_requests - success_requests
        
        # Group by gateway
        gateway_stats = {}
        for log in logs:
            if log.gateway_type not in gateway_stats:
                gateway_stats[log.gateway_type] = {
                    'requests': 0,
                    'tokens': 0,
                    'duration': 0
                }
            stats = gateway_stats[log.gateway_type]
            stats['requests'] += 1
            stats['tokens'] += log.tokens_used or 0
            stats['duration'] += log.request_duration or 0
        
        # Show summary
        summary = {
            'Date Range': f"{start_date.date()} to {end_date.date()}",
            'Total Requests': total_requests,
            'Total Tokens': total_tokens,
            'Total Duration': f"{total_duration}ms",
            'Success Rate': f"{(success_requests/total_requests*100):.1f}%",
            'Error Rate': f"{(error_requests/total_requests*100):.1f}%"
        }
        format_dict(summary, f"Usage Summary for {username}")
        
        # Show gateway breakdown
        headers = ['Gateway', 'Requests', 'Tokens', 'Duration (ms)']
        rows = [
            [
                gateway,
                stats['requests'],
                stats['tokens'],
                stats['duration']
            ]
            for gateway, stats in gateway_stats.items()
        ]
        
        print_table(headers, rows, "Gateway Breakdown")
        
    except Exception as e:
        print_error(f"Failed to generate summary: {str(e)}")
        raise click.Abort()

@usage_cli.command(name='export')
@click.argument('username')
@click.argument('format', type=click.Choice(['json', 'csv']))
@click.option('--gateway', help='Filter by gateway type')
@click.option('--days', type=int, default=30, help='Number of days to export (default: 30)')
@click.option('--model', help='Filter by model name')
@click.option('--output', help='Output file path')
def export_usage(
    username: str,
    format: str,
    gateway: Optional[str],
    days: int,
    model: Optional[str],
    output: Optional[str]
):
    """Export usage data to JSON or CSV format."""
    db = get_db()
    
    try:
        # Find user
        user = db.query(User).filter(User.username == username).first()
        if not user:
            print_error(f"User '{username}' not found")
            raise click.Abort()
        
        # Calculate date range
        end_date = datetime.utcnow()
        start_date = end_date - timedelta(days=days)
        
        # Query usage logs
        query = db.query(GatewayUsageLog).filter(
            GatewayUsageLog.user_id == user.id,
            GatewayUsageLog.timestamp >= start_date
        )
        if gateway:
            query = query.filter(GatewayUsageLog.gateway_type == gateway)
        if model:
            query = query.filter(GatewayUsageLog.model_name == model)
        
        logs = query.order_by(GatewayUsageLog.timestamp.desc()).all()
        
        if not logs:
            print_error(f"No usage logs found for the specified criteria")
            raise click.Abort()
        
        # Prepare export data
        data = [
            {
                'timestamp': log.timestamp.isoformat(),
                'gateway': log.gateway_type,
                'model': log.model_name,
                'tokens': log.tokens_used,
                'duration': log.request_duration,
                'status_code': log.status_code,
                'error_message': log.error_message
            }
            for log in logs
        ]
        
        # Generate output
        if format == 'json':
            output_data = json.dumps(data, indent=2)
            extension = 'json'
        else:  # csv
            output_buffer = StringIO()
            writer = csv.DictWriter(
                output_buffer,
                fieldnames=['timestamp', 'gateway', 'model', 'tokens', 'duration', 'status_code', 'error_message']
            )
            writer.writeheader()
            writer.writerows(data)
            output_data = output_buffer.getvalue()
            extension = 'csv'
        
        # Write to file or print
        if output:
            if not output.endswith(f'.{extension}'):
                output = f"{output}.{extension}"
            with open(output, 'w') as f:
                f.write(output_data)
            print_success(f"Usage data exported to {output}")
        else:
            click.echo(output_data)
        
    except Exception as e:
        print_error(f"Failed to export usage data: {str(e)}")
        raise click.Abort()
