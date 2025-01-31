"""Tests for CLI output formatting utilities."""
import pytest
import click
from datetime import datetime, timezone
from io import StringIO
from unittest.mock import patch

from parallama.cli.utils.output import (
    format_datetime,
    print_error,
    print_success,
    print_warning,
    print_table,
    print_key,
    confirm_action,
    format_dict
)

def test_format_datetime():
    """Test datetime formatting."""
    dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert format_datetime(dt) == "2024-01-01 12:00:00"
    assert format_datetime(None) == "N/A"

@pytest.mark.parametrize("func,color,prefix", [
    (print_error, "red", "Error: "),
    (print_success, "green", ""),
    (print_warning, "yellow", "Warning: ")
])
def test_print_functions(func, color, prefix):
    """Test colored print functions."""
    message = "test message"
    with patch('click.secho') as mock_secho:
        func(message)
        mock_secho.assert_called_once()
        args, kwargs = mock_secho.call_args
        assert args[0] == f"{prefix}{message}"
        assert kwargs.get('fg') == color

def test_print_table():
    """Test table printing."""
    headers = ['Name', 'Value']
    rows = [['test1', 'value1'], ['test2', 'value2']]
    
    with patch('click.secho') as mock_secho, \
         patch('click.echo') as mock_echo:
        # Test with data
        print_table(headers, rows, "Test Table")
        assert mock_secho.called  # Title was printed
        assert mock_echo.called   # Table was printed
        
        # Test with no data
        print_table(headers, [], "Empty Table")
        mock_secho.assert_called_with("No data available", fg="yellow")

def test_print_key():
    """Test API key printing."""
    key = "pk_live_test123"
    description = "Test key"
    
    with patch('click.secho') as mock_secho, \
         patch('click.echo') as mock_echo:
        print_key(key, description)
        
        # Check header was printed
        mock_secho.assert_called_with("\nAPI Key:", fg="blue", bold=True)
        
        # Check key was printed
        assert any(call.args[0] == key for call in mock_echo.call_args_list)
        
        # Check description was printed
        assert any(
            call.args[0] == f"Description: {description}" 
            for call in mock_echo.call_args_list
        )

def test_confirm_action():
    """Test action confirmation."""
    message = "Confirm action?"
    
    # Test confirmation
    with patch('click.confirm', return_value=True) as mock_confirm:
        result = confirm_action(message)
        assert result is True
        mock_confirm.assert_called_with(message, abort=True)
    
    # Test cancellation
    with patch('click.confirm', side_effect=click.Abort), \
         patch('click.echo') as mock_echo, \
         pytest.raises(SystemExit):
        confirm_action(message)
        mock_echo.assert_called_with("\nOperation cancelled.")

def test_format_dict():
    """Test dictionary formatting."""
    data = {
        'string': 'value',
        'number': 42,
        'datetime': datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        'none': None
    }
    
    with patch('click.secho') as mock_secho, \
         patch('click.echo') as mock_echo, \
         patch('click.style') as mock_style:
        
        # Test with title
        format_dict(data, "Test Data")
        mock_secho.assert_called_with("\nTest Data", fg="blue", bold=True)
        
        # Verify all values were printed
        printed_lines = [call.args[0] for call in mock_echo.call_args_list]
        assert any('value' in line for line in printed_lines)
        assert any('42' in line for line in printed_lines)
        assert any('2024-01-01 12:00:00' in line for line in printed_lines)
        assert any('N/A' in line for line in printed_lines)
        
        # Test with empty data
        format_dict({}, "Empty Data")
        mock_secho.assert_called_with("No data available", fg="yellow")

def test_format_dict_key_alignment():
    """Test dictionary key alignment in format_dict."""
    data = {
        'short': 'value',
        'very_long_key': 'value'
    }
    
    with patch('click.style') as mock_style:
        format_dict(data)
        
        # Check that both keys were styled with the same width
        style_calls = mock_style.call_args_list
        assert len(style_calls) == 2
        
        # Extract the format strings used
        format_strings = [
            call.args[0]
            for call in style_calls
        ]
        
        # Verify both keys were padded to the same width
        # The format strings should look like "short         " and "very_long_key  "
        # with padding to match the longest key
        expected_width = len('very_long_key')
        for fmt_str in format_strings:
            # Remove the colon and any trailing spaces
            key = fmt_str.split(':')[0].rstrip()
            # The original key should be left-aligned in a field of width equal to the longest key
            assert len(fmt_str.split(':')[0]) == expected_width
