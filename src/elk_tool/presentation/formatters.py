from collections.abc import Callable
from datetime import datetime
from typing import Any

from elk_tool.infrastructure.utils import get_message_from_source, get_nested_value

# Type alias for column value getter
ColumnGetter = Callable[[dict[str, Any], dict[str, Any]], str]


def format_timestamp(ts_value: Any) -> str:
    if ts_value is None:
        return "-"
    try:
        # Handle milliseconds timestamp (numeric)
        if isinstance(ts_value, int | float):
            dt = datetime.fromtimestamp(ts_value / 1000)
        # Handle string values
        elif isinstance(ts_value, str):
            # Try as numeric string first (milliseconds)
            try:
                ts_float = float(ts_value)
                dt = datetime.fromtimestamp(ts_float / 1000)
            except ValueError:
                # Try parsing ISO format
                ts_value = ts_value.replace("Z", "+00:00")
                if "." in ts_value:
                    dt = datetime.fromisoformat(ts_value[:26])
                else:
                    dt = datetime.fromisoformat(ts_value)
        else:
            return str(ts_value)[:19]
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (ValueError, OSError):
        return str(ts_value)[:19]


# Column definitions for logs command
# Each column: (header, width_or_ratio, is_ratio, value_getter)
LOG_COLUMNS: dict[str, tuple[str, int, bool, ColumnGetter]] = {
    "ts": (
        "Timestamp",
        19,
        False,
        lambda hit, src: format_timestamp(get_nested_value(src, "@timestamp")),
    ),
    "level": ("Level", 6, False, lambda hit, src: src.get("severity_text", "-") or "-"),
    "id": ("ID", 26, False, lambda hit, src: hit.get("_id", "")),
    "host": (
        "Host",
        1,
        True,
        lambda hit, src: get_nested_value(src, "resource.attributes.host.name") or "-",
    ),
    "service": (
        "Service",
        1,
        True,
        lambda hit, src: get_nested_value(src, "resource.attributes.service.name") or "-",
    ),
    "msg": ("Message", 3, True, lambda hit, src: get_message_from_source(src)),
}

DEFAULT_LOG_COLS = "ts,level,host,service,msg"
