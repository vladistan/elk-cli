"""Unit tests for elk_tool.logging module."""

import logging

from elk_tool.infrastructure.logging import get_logger, setup_logging


def test_setup_logging_default_level():
    """Test that setup_logging configures INFO level by default."""
    setup_logging(verbose=False)
    logger = logging.getLogger("elk_tool")

    assert logger.level == logging.INFO
    assert len(logger.handlers) > 0


def test_setup_logging_verbose():
    """Test that setup_logging configures DEBUG level when verbose."""
    setup_logging(verbose=True)
    logger = logging.getLogger("elk_tool")

    assert logger.level == logging.DEBUG


def test_setup_logging_clears_existing_handlers():
    """Test that setup_logging clears existing handlers."""
    logger = logging.getLogger("elk_tool")

    # Add a handler to ensure there's at least one
    handler = logging.StreamHandler()
    logger.addHandler(handler)

    # Call setup_logging - should clear existing and add exactly one
    setup_logging()

    # Should have exactly one handler (the one setup_logging adds)
    assert len(logger.handlers) == 1


def test_get_logger():
    """Test that get_logger returns a logger instance."""
    logger = get_logger("elk_tool.test")

    assert isinstance(logger, logging.Logger)
    assert logger.name == "elk_tool.test"
