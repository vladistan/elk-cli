"""Elk-tool exception hierarchy and exit codes."""

from enum import IntEnum


class ExitCode(IntEnum):
    SUCCESS = 0
    GENERAL_ERROR = 1
    USAGE_ERROR = 2
    INPUT_ERROR = 3
    OUTPUT_ERROR = 4
    NETWORK_ERROR = 5
    TIMEOUT = 6


class ElkToolError(Exception):
    exit_code: ExitCode = ExitCode.GENERAL_ERROR

    def __init__(self, message: str, exit_code: ExitCode | None = None):
        super().__init__(message)
        if exit_code is not None:
            self.exit_code = exit_code


class ConfigurationError(ElkToolError):
    exit_code = ExitCode.INPUT_ERROR


class ConnectionError(ElkToolError):
    exit_code = ExitCode.NETWORK_ERROR


class DocumentNotFoundError(ElkToolError):
    exit_code = ExitCode.INPUT_ERROR

    def __init__(self, index: str, doc_id: str):
        self.index = index
        self.doc_id = doc_id
        super().__init__(f"Document not found: {index}/{doc_id}")


class QueryError(ElkToolError):
    exit_code = ExitCode.GENERAL_ERROR


class ValidationError(ElkToolError):
    exit_code = ExitCode.INPUT_ERROR
