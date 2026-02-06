"""Elk-tool logging configuration."""

import logging
import sys


def setup_logging(verbose: bool = False) -> None:
    """Logs to stderr to keep stdout clean for piping command output."""
    level = logging.DEBUG if verbose else logging.INFO

    logger = logging.getLogger("elk_tool")
    logger.setLevel(level)
    logger.handlers.clear()

    handler = logging.StreamHandler(sys.stderr)
    handler.setLevel(level)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )

    logger.addHandler(handler)
    logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
