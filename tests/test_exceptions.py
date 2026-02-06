"""Unit tests for elk_tool.exceptions module."""

import pytest

from elk_tool.core.exceptions import (
    ConfigurationError,
    ConnectionError,
    DocumentNotFoundError,
    ElkToolError,
    ExitCode,
    QueryError,
    ValidationError,
)


def test_exit_code_enum_values():
    """Test that ExitCode enum has expected values."""
    assert ExitCode.SUCCESS == 0
    assert ExitCode.GENERAL_ERROR == 1
    assert ExitCode.USAGE_ERROR == 2
    assert ExitCode.INPUT_ERROR == 3
    assert ExitCode.NETWORK_ERROR == 5


def test_elk_tool_error_base():
    """Test base ElkToolError exception."""
    error = ElkToolError("test error")
    assert str(error) == "test error"
    assert error.exit_code == ExitCode.GENERAL_ERROR


def test_elk_tool_error_custom_exit_code():
    """Test ElkToolError with custom exit code."""
    error = ElkToolError("test error", exit_code=ExitCode.TIMEOUT)
    assert error.exit_code == ExitCode.TIMEOUT


def test_configuration_error():
    """Test ConfigurationError has correct exit code."""
    error = ConfigurationError("config error")
    assert str(error) == "config error"
    assert error.exit_code == ExitCode.INPUT_ERROR


def test_connection_error():
    """Test ConnectionError has correct exit code."""
    error = ConnectionError("connection failed")
    assert str(error) == "connection failed"
    assert error.exit_code == ExitCode.NETWORK_ERROR


def test_document_not_found_error():
    """Test DocumentNotFoundError formatting and attributes."""
    error = DocumentNotFoundError("logs-2024", "doc123")
    assert error.index == "logs-2024"
    assert error.doc_id == "doc123"
    assert "Document not found" in str(error)
    assert "logs-2024" in str(error)
    assert "doc123" in str(error)
    assert error.exit_code == ExitCode.INPUT_ERROR


def test_query_error():
    """Test QueryError has correct exit code."""
    error = QueryError("query failed")
    assert str(error) == "query failed"
    assert error.exit_code == ExitCode.GENERAL_ERROR


def test_validation_error():
    """Test ValidationError has correct exit code."""
    error = ValidationError("validation failed")
    assert str(error) == "validation failed"
    assert error.exit_code == ExitCode.INPUT_ERROR


def test_exception_hierarchy():
    """Test that all custom exceptions inherit from ElkToolError."""
    assert issubclass(ConfigurationError, ElkToolError)
    assert issubclass(ConnectionError, ElkToolError)
    assert issubclass(DocumentNotFoundError, ElkToolError)
    assert issubclass(QueryError, ElkToolError)
    assert issubclass(ValidationError, ElkToolError)


def test_exceptions_can_be_raised_and_caught():
    """Test that exceptions can be raised and caught properly."""
    with pytest.raises(ElkToolError, match="test error"):
        raise ElkToolError("test error")

    with pytest.raises(DocumentNotFoundError):
        raise DocumentNotFoundError("my-index", "my-doc")

    with pytest.raises(ConnectionError, match="network error"):
        raise ConnectionError("network error")
