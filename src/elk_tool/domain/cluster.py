import json
from typing import Any

import requests
import typer
from rich.console import Console
from rich.table import Table

from elk_tool.core.client import ElkClient
from elk_tool.core.exceptions import ExitCode


def handle_cluster_health(client: ElkClient, raw: bool = False) -> None:
    console = Console()

    try:
        health = client.get_cluster_health()
    except requests.RequestException as e:
        typer.echo(f"Error connecting to cluster: {e}", err=True)
        raise typer.Exit(ExitCode.NETWORK_ERROR) from None

    if raw:
        typer.echo(json.dumps(health, indent=2))
        return

    # Get node information
    nodes = None
    try:
        nodes = client.get_cluster_nodes()
    except requests.RequestException as e:
        console.print(f"\n[yellow]Warning: Could not fetch node details: {e}[/yellow]")

    format_cluster_health(health, nodes)


def handle_shard_status(client: ElkClient, explain: bool = False, raw: bool = False) -> None:
    console = Console()

    try:
        unassigned = client.get_unassigned_shards()
    except requests.RequestException as e:
        typer.echo(f"Error connecting to cluster: {e}", err=True)
        raise typer.Exit(ExitCode.NETWORK_ERROR) from None

    if not unassigned:
        console.print("[green]No unassigned shards - cluster is healthy![/green]")
        return

    if raw and not explain:
        typer.echo(json.dumps(unassigned, indent=2))
        return

    format_shard_status(unassigned)

    if explain:
        try:
            explanation = client.get_allocation_explain()
            if raw:
                typer.echo(json.dumps(explanation, indent=2))
            else:
                format_allocation_explanation(explanation)
        except requests.RequestException as e:
            console.print(f"[red]Error getting explanation: {e}[/red]")

    console.print()


def format_cluster_health(health: dict[str, Any], nodes: list[dict[str, Any]] | None = None) -> None:
    console = Console()

    status = health.get("status", "unknown")
    cluster_name = health.get("cluster_name", "unknown")
    num_nodes = health.get("number_of_nodes", 0)
    num_data_nodes = health.get("number_of_data_nodes", 0)
    active_primary = health.get("active_primary_shards", 0)
    active_shards = health.get("active_shards", 0)
    relocating = health.get("relocating_shards", 0)
    initializing = health.get("initializing_shards", 0)
    unassigned = health.get("unassigned_shards", 0)
    active_pct = health.get("active_shards_percent_as_number", 0)

    status_colors = {"green": "green", "yellow": "yellow", "red": "red"}
    status_color = status_colors.get(status, "white")

    console.print(f"\n[bold]Cluster:[/bold] {cluster_name}")
    console.print(f"[bold]Status:[/bold] [{status_color}]{status.upper()}[/{status_color}]")
    console.print(f"[bold]Nodes:[/bold] {num_nodes} total, {num_data_nodes} data nodes")
    console.print()

    shard_table = Table(title="Shard Status", show_header=True, header_style="bold")
    shard_table.add_column("Category", style="cyan")
    shard_table.add_column("Count", justify="right")

    shard_table.add_row("Active Primary", str(active_primary))
    shard_table.add_row("Active Total", str(active_shards))
    shard_table.add_row("Relocating", str(relocating))
    shard_table.add_row("Initializing", str(initializing))

    if unassigned > 0:
        shard_table.add_row("Unassigned", f"[red]{unassigned}[/red]")
    else:
        shard_table.add_row("Unassigned", str(unassigned))

    shard_table.add_row("Active %", f"{active_pct:.1f}%")
    console.print(shard_table)

    if nodes is not None:
        console.print()
        node_table = Table(title="Nodes", show_header=True, header_style="bold")
        node_table.add_column("Name", style="cyan")
        node_table.add_column("IP")
        node_table.add_column("Heap %", justify="right")
        node_table.add_column("RAM %", justify="right")
        node_table.add_column("CPU %", justify="right")
        node_table.add_column("Load", justify="right")
        node_table.add_column("Role")
        node_table.add_column("Master")

        for node in sorted(nodes, key=lambda x: x.get("name", "")):
            name = node.get("name", "-")
            ip = node.get("ip", "-")
            heap = node.get("heap.percent", "-")
            ram = node.get("ram.percent", "-")
            cpu = node.get("cpu", "-")
            load = node.get("load_1m", "-")
            role = node.get("node.role", "-")
            master = node.get("master", "-")

            if master == "*":
                master = "[green]*[/green]"

            node_table.add_row(name, ip, heap, ram, cpu, load, role, master)

        console.print(node_table)

    console.print()

    if status == "red":
        console.print("[red bold]WARNING: Cluster is RED - some primary shards are unassigned![/red bold]")
        console.print("This means data loss may have occurred. Check for missing nodes.")
    elif status == "yellow":
        console.print("[yellow]Cluster is YELLOW - some replica shards are unassigned.[/yellow]")
        console.print("The cluster is operational but not fully redundant.")
        if unassigned > 0:
            console.print(f"[yellow]{unassigned} shards need to be assigned to restore full redundancy.[/yellow]")


def format_shard_status(unassigned: list[dict[str, Any]]) -> None:
    console = Console()

    if not unassigned:
        console.print("[green]No unassigned shards - cluster is healthy![/green]")
        return

    console.print(f"\n[yellow]Found {len(unassigned)} unassigned shards:[/yellow]\n")

    table = Table(show_header=True, header_style="bold")
    table.add_column("Index", style="cyan")
    table.add_column("Shard", justify="right")
    table.add_column("Type")
    table.add_column("Reason")
    table.add_column("Unassigned For")

    for shard in unassigned:
        shard_type = "Primary" if shard.get("prirep") == "p" else "Replica"
        reason = shard.get("unassigned.reason", "-")
        duration = shard.get("unassigned.for", "-")
        table.add_row(
            shard.get("index", "-"),
            shard.get("shard", "-"),
            shard_type,
            reason,
            duration,
        )

    console.print(table)


def format_allocation_explanation(explanation: dict[str, Any]) -> None:
    console = Console()

    console.print("\n[bold]Allocation Explanation:[/bold]\n")

    if "message" in explanation:
        console.print(explanation["message"])
        return

    index = explanation.get("index", "unknown")
    shard_num = explanation.get("shard", "?")
    primary = explanation.get("primary", False)
    shard_type = "primary" if primary else "replica"

    console.print(f"[cyan]Index:[/cyan] {index}")
    console.print(f"[cyan]Shard:[/cyan] {shard_num} ({shard_type})")

    # Show the reason it can't be allocated
    if "allocate_explanation" in explanation:
        console.print(f"\n[yellow]Reason:[/yellow] {explanation['allocate_explanation']}")

    # Show node decisions
    node_decisions = explanation.get("node_allocation_decisions", [])
    if node_decisions:
        console.print("\n[bold]Node Decisions:[/bold]")
        for node in node_decisions[:5]:  # Show first 5
            node_name = node.get("node_name", "unknown")
            decision = node.get("node_decision", "unknown")
            deciders = node.get("deciders", [])

            console.print(f"\n  [cyan]{node_name}[/cyan]: {decision}")
            for decider in deciders:
                if decider.get("decision") == "NO":
                    console.print(f"    - {decider.get('decider')}: {decider.get('explanation', 'no explanation')}")

    console.print()
