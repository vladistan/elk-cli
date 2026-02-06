"""Document operations for lift and cleanup commands."""

import json
from pathlib import Path
from typing import Any

from elk_tool.core.client import ElkClient


def extract_body_from_source(source: dict[str, Any]) -> str | None:
    body = source.get("body") or source.get("message") or source.get("Body")

    if body is None:
        return None

    if isinstance(body, dict):
        return body.get("text") or body.get("stringValue") or json.dumps(body)

    return str(body)


def save_document_to_file(
    doc: dict[str, Any],
    output_dir: str,
    doc_id: str,
) -> tuple[Path, Path | None]:
    actual_index = doc.get("_index", "unknown")
    actual_index = doc.get("_index", "unknown")

    # Create output directory
    output_path = Path(output_dir) / actual_index
    output_path.mkdir(parents=True, exist_ok=True)

    # Save full document
    doc_file = output_path / f"{doc_id}.json"
    with doc_file.open("w") as f:
        json.dump(doc, f, indent=2)

    # Extract and save body if present
    raw_file = None
    source = doc.get("_source", {})
    body = extract_body_from_source(source)

    if body:
        raw_file = output_path / f"{doc_id}.raw"
        with raw_file.open("w") as f:
            f.write(body)

    return doc_file, raw_file


def cleanup_test_documents(
    client: ElkClient,
    index: str,
    dry_run: bool = False,
) -> tuple[list[str], int]:
    query_body = {"match": {"attributes.int-test": True}}
    result = client.search_documents(index, size=1000, query=query_body)

    hits = result.get("hits", {}).get("hits", [])
    doc_ids = [hit.get("_id") for hit in hits]

    if dry_run or not hits:
        return doc_ids, 0

    deleted = 0
    for hit in hits:
        hit_id = hit.get("_id")
        if client.delete_document(index, hit_id):
            deleted += 1

    return doc_ids, deleted
