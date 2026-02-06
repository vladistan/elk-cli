"""Document operation tests (lift, delete)."""

import json

from elk_tool.ui.cli import app


def _find_billing_doc_id(cli_runner):
    """Helper to find a document ID in billing-* index."""
    list_result = cli_runner.invoke(app, ["list", "billing-*", "-n", "1"])
    assert list_result.exit_code == 0

    lines = list_result.stdout.strip().split("\n")
    for line in lines:
        if not line.strip() or "ID" in line or "---" in line or "Found" in line or "To lift" in line or "Searching" in line:
            continue
        parts = line.split()
        if parts:
            return parts[0]
    return None


def test_lift_command_with_real_document(elk_api_key, cli_runner):
    """Test lift command with a real document from billing- index."""
    doc_id = _find_billing_doc_id(cli_runner)
    assert doc_id is not None, "Should find at least one document in billing-* index"

    lift_result = cli_runner.invoke(app, ["lift", "billing-*", doc_id])
    assert lift_result.exit_code == 0

    doc = json.loads(lift_result.stdout)
    assert "_source" in doc
    assert "_index" in doc
    assert doc["_id"] == doc_id


def test_lift_command_with_output_dir(elk_api_key, cli_runner, tmp_path):
    """Test lift command with --output option saves files correctly."""
    doc_id = _find_billing_doc_id(cli_runner)
    assert doc_id is not None, "Should find at least one document in billing-* index"

    output_dir = tmp_path / "testdata"
    lift_result = cli_runner.invoke(app, ["lift", "billing-*", doc_id, "-o", str(output_dir)])
    assert lift_result.exit_code == 0

    # Verify output messages
    assert "Fetching document" in lift_result.stderr
    assert "Saved document to" in lift_result.stderr
    assert "Done!" in lift_result.stderr

    # Find the actual index directory (billing-* resolves to actual index name)
    index_dirs = list(output_dir.iterdir())
    assert len(index_dirs) == 1
    actual_index_dir = index_dirs[0]

    # Verify JSON file was created
    json_file = actual_index_dir / f"{doc_id}.json"
    assert json_file.exists()

    with json_file.open() as f:
        doc = json.load(f)
    assert "_source" in doc
    assert doc["_id"] == doc_id


def test_lift_command_with_raw_option(elk_api_key, cli_runner):
    """Test lift command with --raw option outputs only message body."""
    doc_id = _find_billing_doc_id(cli_runner)
    assert doc_id is not None, "Should find at least one document in billing-* index"

    lift_result = cli_runner.invoke(app, ["lift", "billing-*", doc_id, "--raw"])
    assert lift_result.exit_code == 0

    # Raw output should NOT be JSON (no curly braces at start)
    # It should be the message body only
    # Note: if document has no body/message field, output may be empty
    output = lift_result.stdout.strip()
    # If there's output, it should not be the full JSON document
    if output:
        assert not output.startswith("{"), "Raw output should not be full JSON"


def _find_oldest_metrics_doc(cli_runner):
    """Helper to find the oldest document in metrics-k8sclusterreceiver stream.

    Returns tuple of (doc_id, actual_index_name) since deletion requires the
    actual backing index, not the datastream alias.
    """
    # Use query with sort to get oldest document
    query = json.dumps({
        "query": {"match_all": {}},
        "size": 1,
        "sort": [{"@timestamp": "asc"}]
    })
    result = cli_runner.invoke(app, [
        "query", query,
        "--index", "metrics-k8sclusterreceiver.otel-default"
    ])
    assert result.exit_code == 0

    # Parse output to extract doc ID and Index
    # Output format includes "ID: <doc_id>" and "Index: <index_name>" lines
    doc_id = None
    index_name = None
    for line in result.stdout.split("\n"):
        if line.startswith("ID:"):
            doc_id = line.split(":", 1)[1].strip()
        elif line.startswith("Index:"):
            index_name = line.split(":", 1)[1].strip()
        if doc_id and index_name:
            break
    return doc_id, index_name


def test_delete_command_with_real_document(elk_api_key, cli_runner):
    """Test delete command with a real document from metrics stream.

    This test finds the oldest document in the metrics-k8sclusterreceiver
    stream and deletes it. Metrics data is constantly being generated so
    deleting old data is safe.
    """
    doc_id, actual_index = _find_oldest_metrics_doc(cli_runner)
    assert doc_id is not None, "Should find at least one document in metrics stream"
    assert actual_index is not None, "Should have actual index name for deletion"

    # Delete with --force to skip interactive confirmation
    # Must use actual backing index, not datastream alias
    delete_result = cli_runner.invoke(app, [
        "delete",
        actual_index,
        doc_id,
        "--force"
    ])
    assert delete_result.exit_code == 0
    assert "Deleting document" in delete_result.stdout
    assert "deleted" in delete_result.stdout.lower()
