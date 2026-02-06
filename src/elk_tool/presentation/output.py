"""Output formatting and table rendering for CLI commands."""

import json
from typing import Any

import typer
from rich.console import Console
from rich.table import Table

from elk_tool.infrastructure.utils import get_nested_value
from elk_tool.presentation.formatters import LOG_COLUMNS, format_timestamp


def print_indices_table(idx_list: list[dict[str, Any]]) -> None:
    typer.echo(f"Found {len(idx_list)} indices:\n")
    typer.echo(f"{'Index':<60} {'Health':<8} {'Docs':<12} {'Size':<10}")
    typer.echo("-" * 95)
    for idx in sorted(idx_list, key=lambda x: x.get("index", "")):
        name = idx.get("index", "")
        health = idx.get("health", "")
        docs = idx.get("docs.count", "0")
        size = idx.get("store.size", "0b")
        typer.echo(f"{name:<60} {health:<8} {docs:<12} {size:<10}")
    typer.echo()


def print_data_streams_table(streams: list[dict[str, Any]]) -> None:
    typer.echo(f"Found {len(streams)} data streams:\n")
    typer.echo(f"{'Name':<60} {'Indices':<8} {'Gen':<5}")
    typer.echo("-" * 75)
    for stream in sorted(streams, key=lambda x: x.get("name", "")):
        name = stream.get("name", "")
        num_indices = len(stream.get("indices", []))
        generation = stream.get("generation", 0)
        typer.echo(f"{name:<60} {num_indices:<8} {generation:<5}")
    typer.echo()


def print_hosts_table(buckets: list[dict[str, Any]]) -> None:
    typer.echo(f"\nFound {len(buckets)} hosts:\n")
    typer.echo(f"{'Hostname':<40} {'Docs':<12}")
    typer.echo("-" * 55)
    for bucket in sorted(buckets, key=lambda x: x.get("key", "")):
        hostname = bucket.get("key", "")
        doc_count = bucket.get("doc_count", 0)
        typer.echo(f"{hostname:<40} {doc_count:<12}")
    typer.echo()


def print_services_table(buckets: list[dict[str, Any]]) -> None:
    typer.echo(f"\nFound {len(buckets)} services:\n")
    typer.echo(f"{'Service':<40} {'Docs':<12}")
    typer.echo("-" * 55)
    for bucket in sorted(buckets, key=lambda x: x.get("key", "")):
        service_name = bucket.get("key", "")
        doc_count = bucket.get("doc_count", 0)
        typer.echo(f"{service_name:<40} {doc_count:<12}")
    typer.echo()


def print_documents_table(hits: list[dict[str, Any]], index: str) -> None:
    typer.echo(f"{'ID':<26} {'Timestamp':<20} {'Message':<50}")
    typer.echo("-" * 100)

    for hit in hits:
        hit_id = hit.get("_id", "")[:26]
        source = hit.get("_source", {})
        ts = get_nested_value(source, "@timestamp")
        ts_str = format_timestamp(ts)
        message = (
            get_nested_value(source, "message")
            or get_nested_value(source, "body")
            or get_nested_value(source, "body.text")
            or ""
        )
        if isinstance(message, dict):
            message = message.get("text", str(message))
        message = str(message).replace("\n", " ")[:50]

        typer.echo(f"{hit_id:<26} {ts_str:<20} {message:<50}")

    typer.echo()

    if hits:
        first_id = hits[0].get("_id")
        typer.echo("To lift a document, run:")
        typer.echo(f"  elk-tool lift {index} {first_id}")


def print_logs_full(hits: list[dict[str, Any]], col_names: list[str]) -> None:
    show_id_in_full = "id" in col_names
    for hit in hits:
        hit_id = hit.get("_id", "")
        source = hit.get("_source", {})
        ts = get_nested_value(source, "@timestamp")
        ts_str = format_timestamp(ts)
        severity = source.get("severity_text", "-")
        host_name = get_nested_value(source, "resource.attributes.host.name") or "-"
        svc = get_nested_value(source, "resource.attributes.service.name") or "-"
        message = (
            get_nested_value(source, "message")
            or get_nested_value(source, "body")
            or get_nested_value(source, "attributes.original_message")
            or ""
        )
        if isinstance(message, dict):
            message = message.get("text", str(message))

        header = f"[{ts_str}] [{severity:<5}] {host_name}/{svc}"
        if show_id_in_full:
            header += f" ({hit_id})"
        typer.echo(header)
        typer.echo(f"  {message}")
        typer.echo()


def print_logs_table(hits: list[dict[str, Any]], col_names: list[str]) -> None:
    console = Console()
    table = Table(show_header=True, header_style="bold", expand=True, box=None)

    for col_name in col_names:
        header, col_size, is_ratio, _ = LOG_COLUMNS[col_name]
        if is_ratio:
            table.add_column(header, no_wrap=True, ratio=col_size)
        else:
            table.add_column(header, no_wrap=True, width=col_size)

    for hit in hits:
        source = hit.get("_source", {})
        row = [LOG_COLUMNS[col_name][3](hit, source) for col_name in col_names]
        table.add_row(*row)

    console.print(table)


def print_mapping_fields(fields_list: list[tuple[str, str]], field_filter: str | None = None) -> None:
    if not fields_list:
        if field_filter:
            typer.echo(f"No fields found matching '{field_filter}'")
        else:
            typer.echo("No fields found")
        return

    typer.echo(f"\nFound {len(fields_list)} fields:\n")
    typer.echo(f"{'Field':<60} {'Type':<15}")
    typer.echo("-" * 75)

    for field_path, field_type in fields_list:
        typer.echo(f"{field_path:<60} {field_type:<15}")

    typer.echo()


def print_full_documents(hits: list[dict[str, Any]]) -> None:
    for hit in hits:
        hit_id = hit.get("_id")
        source = hit.get("_source", {})
        typer.echo(f"ID: {hit_id}")
        typer.echo(json.dumps(source, indent=2))
        typer.echo()


def print_raw_json(hits: list[dict[str, Any]]) -> None:
    for hit in hits:
        typer.echo(json.dumps(hit, indent=2))
        typer.echo()
