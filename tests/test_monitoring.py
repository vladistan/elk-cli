"""Unit tests for elk_tool.monitoring module."""

from elk_tool.infrastructure.monitoring import setup_sentry


def test_setup_sentry_executes_without_error():
    """Test that setup_sentry can be called without errors."""
    # Should not raise any exceptions
    setup_sentry()
    setup_sentry(environment="test")


def test_setup_sentry_accepts_environment_param():
    """Test that setup_sentry accepts environment parameter."""
    # Test various environment strings
    setup_sentry(environment="local")
    setup_sentry(environment="staging")
    setup_sentry(environment="production")
