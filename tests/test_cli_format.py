"""Tests for format_timestamp utility function."""

from elk_tool.presentation.formatters import format_timestamp


def test_format_timestamp_with_none():
    """Test format_timestamp returns '-' for None input."""
    assert format_timestamp(None) == "-"


def test_format_timestamp_with_milliseconds_int():
    """Test format_timestamp with integer milliseconds."""
    # 1704067200000 = 2024-01-01 00:00:00 UTC (converts to local time)
    result = format_timestamp(1704067200000)
    # Just verify it returns a properly formatted datetime string
    assert len(result) == 19  # "YYYY-MM-DD HH:MM:SS"
    assert result[4] == "-" and result[7] == "-"  # Date separators
    assert result[10] == " "  # Space between date and time
    assert result[13] == ":" and result[16] == ":"  # Time separators


def test_format_timestamp_with_milliseconds_float():
    """Test format_timestamp with float milliseconds."""
    result = format_timestamp(1704067200000.0)
    assert len(result) == 19
    assert ":" in result


def test_format_timestamp_with_string_milliseconds():
    """Test format_timestamp with string containing milliseconds."""
    result = format_timestamp("1704067200000")
    assert len(result) == 19
    assert ":" in result


def test_format_timestamp_with_iso_string():
    """Test format_timestamp with ISO format string."""
    result = format_timestamp("2024-01-01T12:30:45.123Z")
    assert "2024-01-01" in result
    assert "12:30:45" in result


def test_format_timestamp_with_iso_string_no_microseconds():
    """Test format_timestamp with ISO format string without microseconds."""
    result = format_timestamp("2024-01-01T12:30:45+00:00")
    assert "2024-01-01" in result
    assert "12:30:45" in result


def test_format_timestamp_with_invalid_string():
    """Test format_timestamp with invalid string returns truncated value."""
    result = format_timestamp("not-a-valid-timestamp-at-all")
    # Should return first 19 chars of the string
    assert result == "not-a-valid-timesta"


def test_format_timestamp_with_unknown_type():
    """Test format_timestamp with unknown type returns truncated string."""
    result = format_timestamp(["some", "list"])
    # Should convert to string and truncate
    assert len(result) <= 19
