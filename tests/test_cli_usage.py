"""Tests for usage reporting CLI commands."""
import pytest
import json
import os
from click.testing import CliRunner
from datetime import datetime, timedelta
from io import StringIO
from unittest.mock import patch

from parallama.cli.commands.usage import usage_cli
from parallama.models.user import User
from parallama.models.rate_limit import GatewayUsageLog
from parallama.core.database import get_db

@pytest.fixture
def cli_runner(db_session):
    """Create a CLI runner with database session."""
    runner = CliRunner()
    def mock_get_db():
        return db_session
    with patch('parallama.cli.commands.usage.get_db', side_effect=mock_get_db):
        yield runner

@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    user = User(username="testuser", role="basic")
    user.set_password("password123")
    db_session.add(user)
    db_session.commit()
    return user

@pytest.fixture
def test_usage_logs(db_session, test_user):
    """Create test usage logs."""
    logs = []
    # Create logs for the last 30 days
    for i in range(30):
        timestamp = datetime.utcnow() - timedelta(days=i)
        log = GatewayUsageLog(
            user_id=test_user.id,
            gateway_type="ollama",
            timestamp=timestamp,
            endpoint="/v1/chat/completions",
            model_name="llama2",
            tokens_used=100 + i,
            request_duration=50 + i,
            status_code=200 if i % 5 != 0 else 500  # Some errors
        )
        logs.append(log)
    
    # Add some logs for a different gateway
    for i in range(5):
        timestamp = datetime.utcnow() - timedelta(days=i)
        log = GatewayUsageLog(
            user_id=test_user.id,
            gateway_type="openai",
            timestamp=timestamp,
            endpoint="/v1/completions",
            model_name="gpt-3.5-turbo",
            tokens_used=150 + i,
            request_duration=75 + i,
            status_code=200
        )
        logs.append(log)
    
    db_session.add_all(logs)
    db_session.commit()
    return logs

def test_list_usage(cli_runner, test_usage_logs):
    """Test listing usage history."""
    result = cli_runner.invoke(
        usage_cli,
        ['list', 'testuser']
    )
    assert result.exit_code == 0
    assert "Usage History for testuser" in result.output
    assert "ollama" in result.output
    assert "openai" in result.output
    assert "llama2" in result.output
    assert "gpt-3.5-turbo" in result.output

def test_list_usage_with_gateway(cli_runner, test_usage_logs):
    """Test listing usage history filtered by gateway."""
    result = cli_runner.invoke(
        usage_cli,
        ['list', 'testuser', '--gateway', 'ollama']
    )
    assert result.exit_code == 0
    assert "Usage History for testuser" in result.output
    assert "ollama" in result.output
    assert "llama2" in result.output
    assert "gpt-3.5-turbo" not in result.output

def test_list_usage_with_model(cli_runner, test_usage_logs):
    """Test listing usage history filtered by model."""
    result = cli_runner.invoke(
        usage_cli,
        ['list', 'testuser', '--model', 'llama2']
    )
    assert result.exit_code == 0
    assert "Usage History for testuser" in result.output
    assert "llama2" in result.output
    assert "gpt-3.5-turbo" not in result.output

def test_list_usage_nonexistent_user(cli_runner):
    """Test listing usage for nonexistent user."""
    result = cli_runner.invoke(
        usage_cli,
        ['list', 'nonexistent']
    )
    assert result.exit_code != 0
    assert "User 'nonexistent' not found" in result.output

def test_list_usage_no_logs(cli_runner, test_user):
    """Test listing usage when no logs exist."""
    result = cli_runner.invoke(
        usage_cli,
        ['list', 'testuser']
    )
    assert result.exit_code != 0
    assert "No usage logs found" in result.output

def test_usage_summary(cli_runner, test_usage_logs):
    """Test usage summary generation."""
    result = cli_runner.invoke(
        usage_cli,
        ['summary', 'testuser']
    )
    assert result.exit_code == 0
    assert "Usage Summary for testuser" in result.output
    assert "Total Requests" in result.output
    assert "Total Tokens" in result.output
    assert "Success Rate" in result.output
    assert "Gateway Breakdown" in result.output
    assert "ollama" in result.output
    assert "openai" in result.output

def test_usage_summary_with_gateway(cli_runner, test_usage_logs):
    """Test usage summary filtered by gateway."""
    result = cli_runner.invoke(
        usage_cli,
        ['summary', 'testuser', '--gateway', 'ollama']
    )
    assert result.exit_code == 0
    assert "Usage Summary for testuser" in result.output
    assert "ollama" in result.output
    assert "openai" not in result.output

def test_usage_summary_nonexistent_user(cli_runner):
    """Test usage summary for nonexistent user."""
    result = cli_runner.invoke(
        usage_cli,
        ['summary', 'nonexistent']
    )
    assert result.exit_code != 0
    assert "User 'nonexistent' not found" in result.output

def test_usage_summary_no_logs(cli_runner, test_user):
    """Test usage summary when no logs exist."""
    result = cli_runner.invoke(
        usage_cli,
        ['summary', 'testuser']
    )
    assert result.exit_code != 0
    assert "No usage logs found" in result.output

def test_export_usage_json(cli_runner, test_usage_logs, tmp_path):
    """Test exporting usage data to JSON."""
    output_file = tmp_path / "usage.json"
    result = cli_runner.invoke(
        usage_cli,
        ['export', 'testuser', 'json', '--output', str(output_file)]
    )
    assert result.exit_code == 0
    assert "Usage data exported" in result.output
    assert output_file.exists()
    
    # Verify JSON content
    with open(output_file) as f:
        data = json.load(f)
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(isinstance(entry, dict) for entry in data)
    assert all(
        key in data[0] 
        for key in ['timestamp', 'gateway', 'model', 'tokens', 'duration', 'status_code']
    )

def test_export_usage_csv(cli_runner, test_usage_logs, tmp_path):
    """Test exporting usage data to CSV."""
    output_file = tmp_path / "usage.csv"
    result = cli_runner.invoke(
        usage_cli,
        ['export', 'testuser', 'csv', '--output', str(output_file)]
    )
    assert result.exit_code == 0
    assert "Usage data exported" in result.output
    assert output_file.exists()
    
    # Verify CSV content
    with open(output_file) as f:
        header = f.readline().strip().split(',')
        assert all(
            field in header 
            for field in ['timestamp', 'gateway', 'model', 'tokens', 'duration', 'status_code']
        )
        assert f.readline()  # At least one data row exists

def test_export_usage_filtered(cli_runner, test_usage_logs, tmp_path):
    """Test exporting filtered usage data."""
    output_file = tmp_path / "usage.json"
    result = cli_runner.invoke(
        usage_cli,
        [
            'export', 'testuser', 'json',
            '--gateway', 'ollama',
            '--model', 'llama2',
            '--output', str(output_file)
        ]
    )
    assert result.exit_code == 0
    
    with open(output_file) as f:
        data = json.load(f)
    assert all(entry['gateway'] == 'ollama' for entry in data)
    assert all(entry['model'] == 'llama2' for entry in data)

def test_export_usage_nonexistent_user(cli_runner):
    """Test exporting usage for nonexistent user."""
    result = cli_runner.invoke(
        usage_cli,
        ['export', 'nonexistent', 'json']
    )
    assert result.exit_code != 0
    assert "User 'nonexistent' not found" in result.output

def test_export_usage_no_logs(cli_runner, test_user):
    """Test exporting usage when no logs exist."""
    result = cli_runner.invoke(
        usage_cli,
        ['export', 'testuser', 'json']
    )
    assert result.exit_code != 0
    assert "No usage logs found" in result.output
