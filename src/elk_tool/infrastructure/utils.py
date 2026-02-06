"""Utility functions for nested values, time parsing, and mapping flattening."""

import re
from typing import Any

# Valid time units for ELK-style time ranges
TIME_UNITS = {
    "s": "seconds",
    "m": "minutes",
    "h": "hours",
    "d": "days",
    "w": "weeks",
    "M": "months",
}


def get_nested_value(source: dict[str, Any], field: str) -> Any:
    """Get a nested value from a dict using dot notation.

    Handles both truly nested dicts and flattened OTel-style keys.
    E.g., both `resource.attributes.host.name` (nested) and
    `resource.attributes` with key `"host.name"` (flattened).
    """
    if not source or not isinstance(source, dict):
        return None

    # First, try direct key lookup (for flattened keys)
    if field in source:
        return source[field]

    parts = field.split(".")
    value = source

    # Try progressively combining parts for flattened keys
    for i in range(len(parts)):
        key = ".".join(parts[: i + 1])
        remainder = ".".join(parts[i + 1 :])

        if isinstance(value, dict) and key in value:
            if remainder:
                # Recurse with remaining path
                result = get_nested_value(value[key], remainder)
                if result is not None:
                    return result
            else:
                return value[key]

        # Try simple nesting for this part
        if isinstance(value, dict) and parts[i] in value:
            value = value[parts[i]]
        else:
            return None

    return value


def parse_time_range(time_str: str) -> str | None:
    if not time_str:
        return None

    match = re.match(r"^(\d+)([smhdwM])$", time_str)
    if not match:
        return None

    return time_str


def get_message_from_source(source: dict[str, Any]) -> str:
    """Extract message text from source document with fallback chain.

    Tries 'message' field first, falls back to 'body', then empty string.
    If value is dict, extracts 'text' key or converts to string.
    """
    message = get_nested_value(source, "message") or get_nested_value(source, "body") or ""
    if isinstance(message, dict):
        message = message.get("text", str(message))
    return str(message).replace("\n", " ")


def flatten_fields(
    properties: dict[str, Any],
    prefix: str = "",
    field_filter: str | None = None,
) -> list[tuple[str, str]]:
    """Recursively flatten nested Elasticsearch mapping properties.

    Traverses nested object properties and builds flat field paths with types.
    When field_filter is provided, only includes fields that start with the filter
    path (the filter is a prefix of the field path).

    Args:
        properties: Elasticsearch mapping properties dict
        prefix: Current field path prefix (builds recursively)
        field_filter: Optional filter - only includes fields starting with this path

    Returns:
        List of (field_path, field_type) tuples, sorted by field_path
    """
    fields = []
    for name, config in sorted(properties.items()):
        full_path = f"{prefix}{name}" if prefix else name

        # Check if this path should be traversed (may contain matching children)
        # or skipped entirely
        if field_filter and not full_path.startswith(field_filter) and not field_filter.startswith(full_path):
            continue

        # Check if this path should be included in output
        # Only include if: no filter, or the field starts with/equals the filter
        should_include = not field_filter or full_path.startswith(field_filter)

        field_type = config.get("type", "object")

        if "properties" in config:
            if should_include:
                fields.append((full_path, "object"))
            fields.extend(flatten_fields(config["properties"], f"{full_path}.", field_filter))
        else:
            if should_include:
                fields.append((full_path, field_type))

    return fields
