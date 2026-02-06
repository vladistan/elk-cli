"""ELK Tool CLI commands."""

import json
import os
from typing import Annotated

import requests
import typer

from elk_tool import __version__
from elk_tool.core.client import ElkClient, get_stream_index
from elk_tool.core.exceptions import ElkToolError, ExitCode
from elk_tool.domain.cluster import handle_cluster_health, handle_shard_status
from elk_tool.domain.documents import (
    cleanup_test_documents,
    extract_body_from_source,
    save_document_to_file,
)
from elk_tool.domain.logs import (
    ValidationError,
    build_filter_description,
    parse_sort_option,
    validate_columns,
    validate_severity,
    validate_time_range,
)
from elk_tool.domain.queries import format_query_response, parse_json_query
from elk_tool.infrastructure.logging import setup_logging
from elk_tool.infrastructure.monitoring import setup_sentry
from elk_tool.infrastructure.utils import flatten_fields
from elk_tool.presentation.formatters import DEFAULT_LOG_COLS
from elk_tool.presentation.output import (
    print_data_streams_table,
    print_documents_table,
    print_full_documents,
    print_hosts_table,
    print_indices_table,
    print_logs_full,
    print_logs_table,
    print_mapping_fields,
    print_raw_json,
    print_services_table,
)
from elk_tool.presentation.prompts import confirm_cleanup, confirm_deletion
from elk_tool.testing.commands import run_sentry_test

app = typer.Typer(
    help="ELK Tool - Query and manage Elasticsearch data.",
    no_args_is_help=True,
)

# Sub-app for test commands
test_app = typer.Typer(help="Test commands for verifying integrations.")
app.add_typer(test_app, name="test")


def version_callback(value: bool) -> None:
    if value:
        typer.echo(f"elk-tool version {__version__}")
        raise typer.Exit()


_active_profile: str | None = None


def get_client() -> ElkClient:
    return ElkClient.from_environment(profile=_active_profile)


@app.callback()
def callback(
    version: Annotated[
        bool,
        typer.Option("--version", "-V", callback=version_callback, is_eager=True),
    ] = False,
    verbose: Annotated[
        bool,
        typer.Option("--verbose", "-v", help="Enable verbose logging"),
    ] = False,
    profile: Annotated[
        str | None,
        typer.Option("--profile", "-P", help="Use named endpoint profile"),
    ] = None,
) -> None:
    global _active_profile
    _active_profile = profile
    setup_logging(verbose=verbose)
    setup_sentry(environment=os.environ.get("ENVIRONMENT", "local"))


@app.command()
def query(
    query_json: Annotated[str, typer.Argument(help="JSON query body")],
    index: Annotated[
        str, typer.Option("--index", "-i", help="Index to query")
    ] = "logs-generic.otel-default",
    size: Annotated[int, typer.Option("--size", "-n", help="Number of documents")] = 10,
    raw: Annotated[bool, typer.Option("--raw", help="Output raw JSON response")] = False,
) -> None:
    """
    Execute a raw Elasticsearch query.

    QUERY_JSON is a JSON query body (e.g., '{"query": {"match_all": {}}}').

    Examples:
        elk-tool query '{"query": {"match_all": {}}}' -n 5
        elk-tool query '{"size": 0, "aggs": {"hosts": {"terms": {"field": "host.name"}}}}' -i logs-*
    """
    client = get_client()

    try:
        query_body = parse_json_query(query_json)
    except ValueError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(ExitCode.INPUT_ERROR) from None

    result = client.raw_query(index, query_body, size)
    typer.echo(format_query_response(result, raw=raw))


@app.command()
def lift(
    index: Annotated[str, typer.Argument(help="Index name or pattern")],
    doc_id: Annotated[str, typer.Argument(help="Document ID")],
    delete_after: Annotated[
        bool, typer.Option("--delete-after", help="Delete document after lifting")
    ] = False,
    output_dir: Annotated[
        str | None, typer.Option("--output", "-o", help="Save to directory (default: output to stdout)")
    ] = None,
    raw: Annotated[
        bool, typer.Option("--raw", "-r", help="Output only the message body (not full JSON)")
    ] = False,
) -> None:
    """
    Lift a document from ELK.

    By default, outputs to stdout. Use -o to save to <output-dir>/<index>/<doc_id>.json.

    Examples:
        elk-tool lift INDEX DOC_ID              # Output JSON to stdout
        elk-tool lift INDEX DOC_ID -r           # Output only message body
        elk-tool lift INDEX DOC_ID -o testdata  # Save to testdata/<index>/<doc_id>.json
    """
    client = get_client()
    doc = client.get_document(index, doc_id)

    if output_dir:
        typer.echo(f"Fetching document: {index}/{doc_id}", err=True)
        doc_file, raw_file = save_document_to_file(doc, output_dir, doc_id)
        typer.echo(f"Saved document to: {doc_file}", err=True)
        if raw_file:
            typer.echo(f"Extracted body to: {raw_file}", err=True)
        typer.echo("Done!", err=True)
    else:
        if raw:
            source = doc.get("_source", {})
            body = extract_body_from_source(source)
            if body:
                typer.echo(body)
        else:
            typer.echo(json.dumps(doc, indent=2))

    if delete_after:
        typer.echo("Deleting document from ELK...", err=True)
        if client.delete_document(index, doc_id):
            typer.echo(f"Document deleted: {index}/{doc_id}", err=True)


@app.command()
def delete(
    index: Annotated[str, typer.Argument(help="Index name or pattern")],
    doc_id: Annotated[str, typer.Argument(help="Document ID")],
    force: Annotated[bool, typer.Option("--force", "-f", help="Skip confirmation")] = False,
) -> None:
    """
    Delete a document from Elasticsearch.

    Prompts for confirmation unless --force is used.

    Examples:
        elk-tool delete INDEX DOC_ID           # Confirm before delete
        elk-tool delete INDEX DOC_ID --force   # Delete without confirmation
    """
    client = get_client()

    if not force and not confirm_deletion(index, doc_id):
        raise typer.Abort()

    typer.echo(f"Deleting document: {index}/{doc_id}")
    if client.delete_document(index, doc_id):
        typer.echo("Document deleted successfully")
    else:
        typer.echo("Document not found or already deleted")


@app.command("list")
def list_docs(
    index: Annotated[str, typer.Argument(help="Index name or pattern")],
    size: Annotated[int, typer.Option("--size", "-n", help="Number of documents")] = 10,
    query: Annotated[
        str | None, typer.Option("--query", "-q", help="Elasticsearch query JSON")
    ] = None,
    full: Annotated[bool, typer.Option("--full", help="Show full document source")] = False,
) -> None:
    """Useful for finding test candidates to lift or debug."""
    client = get_client()

    parsed_query = None
    if query:
        try:
            parsed_query = parse_json_query(query)
        except ValueError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(ExitCode.INPUT_ERROR) from None

    typer.echo(f"Searching {index} for {size} recent documents...")
    result = client.search_documents(index, size, parsed_query)

    hits = result.get("hits", {}).get("hits", [])
    total = result.get("hits", {}).get("total", {}).get("value", 0)

    typer.echo(f"Found {total} total documents, showing {len(hits)}:\n")

    if full:
        print_full_documents(hits)
    else:
        print_documents_table(hits, index)


@app.command()
def cleanup(
    index: Annotated[str, typer.Argument(help="Index name or pattern")],
    dry_run: Annotated[bool, typer.Option("--dry-run", help="Show what would be deleted")] = False,
) -> None:
    """Only deletes documents with attributes.int-test=true marker."""
    client = get_client()

    typer.echo(f"Searching for test documents in {index}...")
    doc_ids, _ = cleanup_test_documents(client, index, dry_run=True)
    total = len(doc_ids)

    typer.echo(f"Found {total} test documents")

    if not doc_ids:
        typer.echo("No test documents to clean up")
        return

    if dry_run:
        typer.echo("Dry run - would delete:")
        for doc_id in doc_ids:
            typer.echo(f"  {doc_id}")
        return

    if not confirm_cleanup(total):
        typer.echo("Aborted")
        return

    _, deleted = cleanup_test_documents(client, index, dry_run=False)
    typer.echo(f"Deleted {deleted} documents")


@app.command()
def indices(
    pattern: Annotated[str, typer.Argument(help="Index/data stream pattern (default: *)")] = "*",
    data_streams: Annotated[
        bool, typer.Option("--data-streams", "-d", help="Show only data streams")
    ] = False,
) -> None:
    client = get_client()

    if data_streams:
        streams = client.list_data_streams(pattern)
        if not streams:
            typer.echo("No data streams found")
            return

        print_data_streams_table(streams)
    else:
        idx_list = client.list_indices(pattern)

        if not idx_list:
            typer.echo("No indices found")
            return

        print_indices_table(idx_list)


@app.command("cluster-health")
def cluster_health(
    raw: Annotated[bool, typer.Option("--raw", help="Output raw JSON response")] = False,
) -> None:
    """Useful for diagnosing cluster issues after node failures."""
    client = get_client()
    handle_cluster_health(client, raw)


@app.command("shard-status")
def shard_status(
    explain: Annotated[bool, typer.Option("--explain", "-e", help="Show allocation explanation")] = False,
    raw: Annotated[bool, typer.Option("--raw", help="Output raw JSON response")] = False,
) -> None:
    """Use --explain for detailed allocation explanation when shards are stuck."""
    client = get_client()
    handle_shard_status(client, explain, raw)


@app.command()
def mapping(
    index: Annotated[str, typer.Argument(help="Index name or pattern")] = "logs-generic.otel-default",
    field: Annotated[str | None, typer.Option("--field", "-f", help="Filter to specific field path")] = None,
    raw: Annotated[bool, typer.Option("--raw", help="Output raw JSON mapping")] = False,
) -> None:
    """
    Examples:
        elk-tool mapping                           # Show all fields
        elk-tool mapping -f attributes             # Show attributes.* fields
        elk-tool mapping -f attributes.net         # Show attributes.net.* fields
        elk-tool mapping --raw                     # Output raw JSON
    """
    client = get_client()

    typer.echo(f"Fetching mapping for {index}...")
    result = client.get_mapping(index)

    if raw:
        typer.echo(json.dumps(result, indent=2))
        return

    if not result:
        typer.echo("No mapping found")
        return

    first_index = next(iter(result.values()))
    properties = first_index.get("mappings", {}).get("properties", {})

    fields_list = flatten_fields(properties, field_filter=field)

    print_mapping_fields(fields_list, field)


# =============================================================================
# Porcelain Commands (user-friendly, smart defaults)
# =============================================================================


@app.command()
def hosts(
    stream: Annotated[
        str, typer.Option("--stream", "-s", help="Stream type: logs or metrics")
    ] = "logs",
    service: Annotated[str | None, typer.Option("--service", help="Filter by service name")] = None,
    time: Annotated[
        str | None,
        typer.Option("--time", "-t", help="Time range: 5m, 15m, 1h, 8h, 24h, 7d, 2w, 1M"),
    ] = None,
) -> None:
    client = get_client()
    index = get_stream_index(stream)

    time_range = None
    if time:
        try:
            time_range = validate_time_range(time)
        except ValidationError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from None

    query = None
    if service:
        query = {"term": {"resource.attributes.service.name": service}}

    desc = f"Fetching unique hosts from {stream}"
    if time_range:
        desc += f" (last {time_range})"
    typer.echo(f"{desc}...")
    buckets = client.aggregate_field(index, "resource.attributes.host.name", query=query, time_range=time_range)

    if not buckets:
        typer.echo("No hosts found")
        return

    print_hosts_table(buckets)


@app.command()
def services(
    stream: Annotated[
        str, typer.Option("--stream", "-s", help="Stream type: logs or metrics")
    ] = "logs",
    host: Annotated[str | None, typer.Option("--host", "-h", help="Filter by hostname")] = None,
    time: Annotated[
        str | None,
        typer.Option("--time", "-t", help="Time range: 5m, 15m, 1h, 8h, 24h, 7d, 2w, 1M"),
    ] = None,
) -> None:
    client = get_client()
    index = get_stream_index(stream)

    time_range = None
    if time:
        try:
            time_range = validate_time_range(time)
        except ValidationError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from None

    query = None
    if host:
        query = {"term": {"resource.attributes.host.name": host}}

    desc = f"Fetching unique services from {stream}"
    if time_range:
        desc += f" (last {time_range})"
    typer.echo(f"{desc}...")
    buckets = client.aggregate_field(index, "resource.attributes.service.name", query=query, time_range=time_range)

    if not buckets:
        typer.echo("No services found")
        return

    print_services_table(buckets)


@app.command()
def logs(
    host: Annotated[str | None, typer.Option("--host", "-h", help="Filter by hostname")] = None,
    service: Annotated[
        str | None, typer.Option("--service", "-s", help="Filter by service name")
    ] = None,
    container: Annotated[
        str | None, typer.Option("--container", "-C", help="Filter by container name")
    ] = None,
    level: Annotated[
        str | None,
        typer.Option(
            "--level", "-l", help="Minimum severity: trace, debug, info, warn, error, fatal"
        ),
    ] = None,
    time: Annotated[
        str | None,
        typer.Option("--time", "-t", help="Time range: 5m, 15m, 1h, 8h, 24h, 7d, 2w, 1M"),
    ] = None,
    search: Annotated[
        str | None, typer.Option("--search", "-S", help="Search text in message body")
    ] = None,
    size: Annotated[int, typer.Option("--size", "-n", help="Number of logs")] = 20,
    cols: Annotated[
        str, typer.Option("--cols", "-c", help="Columns to show: ts,level,id,host,service,msg")
    ] = DEFAULT_LOG_COLS,
    sort: Annotated[
        str, typer.Option("--sort", help="Sort field and order (e.g., '@timestamp:desc')")
    ] = "@timestamp:desc",
    full: Annotated[bool, typer.Option("--full", help="Show full log details")] = False,
    raw: Annotated[bool, typer.Option("--raw", help="Output raw JSON documents")] = False,
) -> None:
    """
    Examples:
        elk-tool logs                                   # Recent logs
        elk-tool logs -t 15m                            # Last 15 minutes
        elk-tool logs -t 1h                             # Last hour
        elk-tool logs -t 24h                            # Last 24 hours
        elk-tool logs -t 7d                             # Last week
        elk-tool logs -h firewall7                      # Logs from host
        elk-tool logs -s litellm                        # Logs from service
        elk-tool logs -C sentry-self-hosted-nginx-1     # Logs from container
        elk-tool logs -h sentry -C pgbouncer            # Host AND container
        elk-tool logs -l error                          # ERROR and above
        elk-tool logs -t 1h -l error                    # Errors in last hour
        elk-tool logs -S "connection refused"           # Search in message
        elk-tool logs -c ts,level,id,msg                # Custom columns
        elk-tool logs --sort severity_number:desc       # Sort by severity
    """
    client = get_client()
    index = get_stream_index("logs")

    # Validate inputs using logs_query_builder
    try:
        col_names = validate_columns(cols)
    except ValidationError as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1) from None

    min_severity = None
    if level:
        try:
            min_severity = validate_severity(level)
        except ValidationError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from None

    time_range = None
    if time:
        try:
            time_range = validate_time_range(time)
        except ValidationError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(1) from None

    sort_field, sort_order = parse_sort_option(sort)

    # Build and display filter description
    filter_desc = build_filter_description(time_range, host, service, container, level, search)
    desc = f"Fetching {size} logs"
    if filter_desc:
        desc += f" {filter_desc}"
    typer.echo(f"{desc}...")

    result = client.search_logs(
        index,
        size=size,
        host=host,
        service=service,
        container=container,
        min_severity=min_severity,
        search_text=search,
        time_range=time_range,
        sort_field=sort_field,
        sort_order=sort_order,
    )

    hits = result.get("hits", {}).get("hits", [])
    total = result.get("hits", {}).get("total", {}).get("value", 0)

    typer.echo(f"Found {total} total, showing {len(hits)}:\n")

    if not hits:
        typer.echo("No logs found")
        return

    if raw:
        print_raw_json(hits)
        return

    if full:
        print_logs_full(hits, col_names)
    else:
        print_logs_table(hits, col_names)

    typer.echo()


@test_app.command("sentry")
def test_sentry() -> None:
    """Verify Sentry integration is working.

    Check Sentry console after running:
    1. Error appears in Issues with correct project/environment/release
    2. Transaction appears in Performance with parent/child spans
    """
    run_sentry_test()


def main() -> None:
    try:
        app()
    except ElkToolError as e:
        typer.echo(f"Error: {e}", err=True)
        raise SystemExit(e.exit_code) from None
    except requests.RequestException as e:
        typer.echo(f"Error: Network request failed: {e}", err=True)
        raise SystemExit(ExitCode.NETWORK_ERROR) from None
