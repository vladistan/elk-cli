"""Log query validation and filter building."""

from elk_tool.core.client import SEVERITY_LEVELS
from elk_tool.infrastructure.utils import parse_time_range
from elk_tool.presentation.formatters import LOG_COLUMNS


class ValidationError(Exception):
    pass


def validate_columns(cols: str) -> list[str]:
    col_names = [c.strip() for c in cols.split(",") if c.strip()]
    invalid_cols = [c for c in col_names if c not in LOG_COLUMNS]

    if invalid_cols:
        raise ValidationError(
            f"Invalid column(s): {', '.join(invalid_cols)}. "
            f"Available: {', '.join(LOG_COLUMNS.keys())}"
        )

    return col_names


def validate_severity(level: str) -> int:
    level_lower = level.lower()
    if level_lower not in SEVERITY_LEVELS:
        raise ValidationError(
            f"Invalid level '{level}'. Use: trace, debug, info, warn, error, fatal"
        )
    return SEVERITY_LEVELS[level_lower]


def validate_time_range(time_str: str) -> str:
    result = parse_time_range(time_str)
    if not result:
        raise ValidationError(
            f"Invalid time range '{time_str}'. Use: 5m, 15m, 1h, 8h, 24h, 7d, 2w, 1M"
        )
    return result


def parse_sort_option(sort: str) -> tuple[str, str]:
    """Defaults to desc if order not specified."""
    sort_parts = sort.split(":")
    sort_field = sort_parts[0]
    sort_order = "desc"

    if len(sort_parts) > 1 and sort_parts[1].lower() in ("asc", "desc"):
        sort_order = sort_parts[1].lower()

    return sort_field, sort_order


def build_filter_description(
    time_range: str | None = None,
    host: str | None = None,
    service: str | None = None,
    container: str | None = None,
    level: str | None = None,
    search: str | None = None,
) -> str:
    filters_desc = []

    if time_range:
        filters_desc.append(f"last {time_range}")
    if host:
        filters_desc.append(f"host={host}")
    if service:
        filters_desc.append(f"service={service}")
    if container:
        filters_desc.append(f"container={container}")
    if level:
        filters_desc.append(f"level>={level}")
    if search:
        filters_desc.append(f"search='{search}'")

    if filters_desc:
        return f"({', '.join(filters_desc)})"
    return ""
