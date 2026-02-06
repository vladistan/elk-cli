"""Query operations for Elasticsearch responses."""

import json
from typing import Any


def parse_json_query(query_json: str) -> dict[str, Any]:
    try:
        result: dict[str, Any] = json.loads(query_json)
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON query: {e}") from e


def format_query_response(result: dict[str, Any], raw: bool = False) -> str:
    """Format query response for display.

    Returns formatted string. If raw=True, returns full JSON.
    Otherwise, formats aggregations and hits separately.
    """
    if raw:
        return json.dumps(result, indent=2)

    output_parts = []

    # Check if response contains aggregations
    aggregations = result.get("aggregations")
    if aggregations:
        output_parts.append("Aggregations:\n")
        output_parts.append(json.dumps(aggregations, indent=2))
        output_parts.append("")

    hits = result.get("hits", {}).get("hits", [])
    total = result.get("hits", {}).get("total", {}).get("value", 0)

    # Only show hits if there are any (aggregation-only queries have size=0)
    if hits:
        output_parts.append(f"Found {total} total documents, showing {len(hits)}:\n")

        for hit in hits:
            output_parts.append(f"ID: {hit.get('_id')}")
            output_parts.append(f"Index: {hit.get('_index')}")
            source = hit.get("_source", {})
            output_parts.append(json.dumps(source, indent=2))
            output_parts.append("")
    elif not aggregations:
        output_parts.append(f"Found {total} total documents, no hits returned.")

    return "\n".join(output_parts)
