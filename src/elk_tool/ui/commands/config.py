import json
from typing import Annotated

import requests
import typer
from rich.console import Console
from rich.table import Table

from elk_tool.core.config import load_config
from elk_tool.core.exceptions import ConfigurationError

config_app = typer.Typer(help="Configuration management commands", no_args_is_help=True)
console = Console()
error_console = Console(stderr=True)


def mask_secret(value: str | None) -> str:
    if not value:
        return "—"
    if len(value) <= 4:
        return "***"
    return f"***...{value[-4:]}"


@config_app.command("profiles")
def list_profiles(
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table or json"),
    ] = "table",
) -> None:
    """List configured profile names with default marked.

    Examples:
        elk-tool config profiles
        elk-tool config profiles --format json
    """
    try:
        app_config = load_config()
    except ConfigurationError as e:
        error_console.print(f"[red]Config error: {e}[/red]")
        raise typer.Exit(1) from e

    if not app_config.profiles:
        console.print("No profiles configured.")
        return

    rows = [
        {"name": name, "default": "*" if name == app_config.default_profile else ""}
        for name in app_config.profiles
    ]

    if format == "json":
        print(json.dumps(rows, indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan")
    table.add_column("Default", justify="center")

    for row in rows:
        table.add_row(row["name"], row["default"])

    console.print(table)
    console.print(f"[dim]{len(rows)} profiles[/dim]")


@config_app.command("show")
def show(
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table or json"),
    ] = "table",
) -> None:
    """Display full configuration with masked API keys and passwords.

    Examples:
        elk-tool config show
        elk-tool config show --format json
    """
    try:
        app_config = load_config()
    except ConfigurationError as e:
        error_console.print(f"[red]Config error: {e}[/red]")
        raise typer.Exit(1) from e

    if not app_config.profiles:
        console.print("No profiles configured.")
        return

    rows = [
        {
            "name": name,
            "default": "*" if name == app_config.default_profile else "",
            "url": profile.url,
            "api_key": mask_secret(profile.api_key),
            "username": profile.username or "—",
            "password": mask_secret(profile.password),
        }
        for name, profile in app_config.profiles.items()
    ]

    if format == "json":
        print(json.dumps(rows, indent=2))
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Name", style="cyan", no_wrap=True)
    table.add_column("Default", justify="center")
    table.add_column("URL")
    table.add_column("API Key", style="dim")
    table.add_column("Username")
    table.add_column("Password", style="dim")

    for row in rows:
        table.add_row(
            row["name"],
            row["default"],
            row["url"],
            row["api_key"],
            row["username"],
            row["password"],
        )

    console.print(table)
    console.print(f"[dim]{len(rows)} profiles[/dim]")


@config_app.command("validate")
def validate(
    format: Annotated[
        str,
        typer.Option("--format", "-f", help="Output format: table or json"),
    ] = "table",
) -> None:
    """Verify connectivity to all configured Elasticsearch profiles.

    Pings each profile's endpoint and reports cluster name on success.

    Examples:
        elk-tool config validate
        elk-tool config validate --format json
    """
    try:
        app_config = load_config()
    except ConfigurationError as e:
        error_console.print(f"[red]Config error: {e}[/red]")
        raise typer.Exit(1) from e

    if not app_config.profiles:
        console.print("No profiles configured.")
        return

    rows: list[dict[str, str]] = []
    for profile_name, profile in app_config.profiles.items():
        headers = {}
        auth = None

        if profile.api_key:
            headers["Authorization"] = f"ApiKey {profile.api_key}"
        elif profile.username and profile.password:
            auth = (profile.username, profile.password)

        try:
            resp = requests.get(
                profile.url,
                headers=headers,
                auth=auth,
                timeout=profile.timeout,
                verify=profile.verify_tls,
            )
            resp.raise_for_status()
            data = resp.json()
            cluster_name = data.get("cluster_name", "unknown")
            rows.append(
                {
                    "profile": profile_name,
                    "status": "OK",
                    "details": f"cluster: {cluster_name}",
                }
            )
        except requests.RequestException as e:
            rows.append(
                {
                    "profile": profile_name,
                    "status": "FAIL",
                    "details": str(e),
                }
            )

    has_failures = any(r["status"] == "FAIL" for r in rows)

    if format == "json":
        print(json.dumps(rows, indent=2))
        if has_failures:
            raise typer.Exit(1)
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Profile", style="cyan", no_wrap=True)
    table.add_column("Status")
    table.add_column("Details")

    for row in rows:
        status_style = "green" if row["status"] == "OK" else "red"
        table.add_row(
            row["profile"],
            f"[{status_style}]{row['status']}[/{status_style}]",
            row["details"],
        )

    console.print(table)

    if has_failures:
        raise typer.Exit(1)
