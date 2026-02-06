"""Advanced CLI command option tests."""

import json

from elk_tool.ui.cli import app

# --- cleanup command tests ---

def test_cleanup_command_dry_run(elk_api_key, cli_runner):
    """Test cleanup command with --dry-run shows what would be deleted.

    Dry run mode is safe - it only searches and reports, doesn't delete.
    """
    result = cli_runner.invoke(app, ["cleanup", "logs-*", "--dry-run"])

    assert result.exit_code == 0
    assert "Searching for test documents" in result.stdout
    assert "Found" in result.stdout
    # May find 0 or more test documents - both are valid outcomes


def test_cleanup_command_dry_run_no_documents(elk_api_key, cli_runner):
    """Test cleanup command dry run when no test documents exist.

    Using billing-* which is unlikely to have int-test:true documents.
    """
    result = cli_runner.invoke(app, ["cleanup", "billing-*", "--dry-run"])

    assert result.exit_code == 0
    assert "Searching for test documents" in result.stdout
    # Should report found count and either list docs or say "no documents"
    assert "Found" in result.stdout or "No test documents" in result.stdout


def test_cleanup_command_dry_run_output_completeness(elk_api_key, cli_runner):
    """Test cleanup command dry-run outputs correct messages for all paths.

    Verifies that dry-run either shows 'No test documents' or 'Dry run - would delete:'
    with document IDs when test documents exist.
    """
    result = cli_runner.invoke(app, ["cleanup", "logs-*", "--dry-run"])

    assert result.exit_code == 0
    assert "Searching for test documents" in result.stdout

    # Must follow one of two paths:
    if "No test documents to clean up" in result.stdout:
        # Path 1: No documents found - message should be clear
        assert "Found 0 test documents" in result.stdout or "No test documents" in result.stdout
    else:
        # Path 2: Documents found - dry-run should list what would be deleted
        assert "Found" in result.stdout
        # When documents exist, dry-run MUST show this message (not silently skip)
        if "Found 0" not in result.stdout:
            assert "Dry run - would delete:" in result.stdout


# --- list command additional tests ---

def test_list_command_with_query_option(elk_api_key, cli_runner):
    """Test list command with --query option for custom ES query."""
    query = json.dumps({"match_all": {}})
    result = cli_runner.invoke(app, ["list", "billing-*", "-n", "1", "--query", query])

    assert result.exit_code == 0
    assert "Found" in result.stdout or "ID" in result.stdout


def test_list_command_with_full_option(elk_api_key, cli_runner):
    """Test list command with --full option shows complete document source."""
    result = cli_runner.invoke(app, ["list", "billing-*", "-n", "1", "--full"])

    assert result.exit_code == 0
    # Full output should contain JSON-like content with _source fields
    # Billing documents typically have timestamp and other fields
    assert "@timestamp" in result.stdout or "_source" in result.stdout or "{" in result.stdout


# --- indices command additional tests ---

def test_indices_command_with_datastreams_option(elk_api_key, cli_runner):
    """Test indices command with --data-streams option shows only data streams."""
    result = cli_runner.invoke(app, ["indices", "--data-streams"])

    assert result.exit_code == 0
    # Should show data streams with header columns
    assert "data streams" in result.stdout.lower() or "Name" in result.stdout
    # Data stream output has Gen column for generation number
    if "Found" in result.stdout:
        assert "Gen" in result.stdout


def test_indices_command_with_datastreams_pattern(elk_api_key, cli_runner):
    """Test indices command with --data-streams and specific pattern."""
    result = cli_runner.invoke(app, ["indices", "metrics-*", "-d"])

    assert result.exit_code == 0
    # Should show filtered data streams or "No data streams found"
    assert "data streams" in result.stdout.lower() or "No data streams" in result.stdout


# --- shard-status command additional tests ---

def test_shard_status_command_with_explain_option(elk_api_key, cli_runner):
    """Test shard-status command with --explain option.

    If cluster is healthy (no unassigned shards), explains nothing.
    If unhealthy, shows allocation explanation.
    """
    result = cli_runner.invoke(app, ["shard-status", "--explain"])

    assert result.exit_code == 0
    # Either healthy cluster or shows explanation
    assert "healthy" in result.stdout.lower() or "unassigned" in result.stdout.lower() or "Allocation" in result.stdout


def test_shard_status_command_with_raw_option(elk_api_key, cli_runner):
    """Test shard-status command with --raw option for JSON output."""
    result = cli_runner.invoke(app, ["shard-status", "--raw"])

    assert result.exit_code == 0
    # Either healthy message or raw JSON output
    assert "healthy" in result.stdout.lower() or result.stdout.strip().startswith("[") or result.stdout.strip().startswith("{")


def test_shard_status_command_with_explain_and_raw(elk_api_key, cli_runner):
    """Test shard-status command with both --explain and --raw options."""
    result = cli_runner.invoke(app, ["shard-status", "--explain", "--raw"])

    assert result.exit_code == 0
    # Either healthy or JSON output
    assert "healthy" in result.stdout.lower() or "[" in result.stdout or "{" in result.stdout


# --- hosts command additional tests ---

def test_hosts_command_with_valid_time_range(elk_api_key, cli_runner):
    """Test hosts command with valid --time option."""
    result = cli_runner.invoke(app, ["hosts", "--time", "1h"])

    assert result.exit_code == 0
    assert "Fetching unique hosts" in result.stdout
    assert "last 1h" in result.stdout or "hosts" in result.stdout.lower()


def test_hosts_command_with_24h_time_range(elk_api_key, cli_runner):
    """Test hosts command with 24h time range."""
    result = cli_runner.invoke(app, ["hosts", "-t", "24h"])

    assert result.exit_code == 0
    assert "Fetching unique hosts" in result.stdout


def test_hosts_command_with_invalid_time_range(elk_api_key, cli_runner):
    """Test hosts command with invalid --time option shows error."""
    result = cli_runner.invoke(app, ["hosts", "--time", "invalid"])

    assert result.exit_code == 1
    assert "Invalid time range" in result.stderr or "Invalid time range" in result.stdout
    assert "5m, 15m, 1h" in result.stderr or "5m, 15m, 1h" in result.stdout


# --- services command additional tests ---

def test_services_command_with_valid_time_range(elk_api_key, cli_runner):
    """Test services command with valid --time option."""
    result = cli_runner.invoke(app, ["services", "--time", "1h"])

    assert result.exit_code == 0
    assert "Fetching unique services" in result.stdout
    assert "last 1h" in result.stdout or "services" in result.stdout.lower()


def test_services_command_with_24h_time_range(elk_api_key, cli_runner):
    """Test services command with 24h time range."""
    result = cli_runner.invoke(app, ["services", "-t", "24h"])

    assert result.exit_code == 0
    assert "Fetching unique services" in result.stdout


def test_services_command_with_invalid_time_range(elk_api_key, cli_runner):
    """Test services command with invalid --time option shows error."""
    result = cli_runner.invoke(app, ["services", "--time", "invalid"])

    assert result.exit_code == 1
    assert "Invalid time range" in result.stderr or "Invalid time range" in result.stdout
    assert "5m, 15m, 1h" in result.stderr or "5m, 15m, 1h" in result.stdout


def test_services_command_with_host_option(elk_api_key, cli_runner):
    """Test services command with --host option filters by hostname.

    Uses cicd-dkr2 which is a consistently active host.
    """
    result = cli_runner.invoke(app, ["services", "--host", "cicd-dkr2"])

    assert result.exit_code == 0
    assert "Fetching unique services" in result.stdout
    # Should find services or report none for this host
    assert "Found" in result.stdout or "No services found" in result.stdout


def test_services_command_with_host_short_option(elk_api_key, cli_runner):
    """Test services command with -h short option for host."""
    result = cli_runner.invoke(app, ["services", "-h", "cicd-dkr2"])

    assert result.exit_code == 0
    assert "Fetching unique services" in result.stdout


def test_services_command_with_host_and_time(elk_api_key, cli_runner):
    """Test services command with both --host and --time options."""
    result = cli_runner.invoke(app, ["services", "--host", "cicd-dkr2", "--time", "1h"])

    assert result.exit_code == 0
    assert "Fetching unique services" in result.stdout
    assert "last 1h" in result.stdout


def test_services_command_with_nonexistent_host(elk_api_key, cli_runner):
    """Test services command with non-existent host returns no services."""
    result = cli_runner.invoke(app, ["services", "--host", "nonexistent-host-xyz123"])

    assert result.exit_code == 0
    assert "No services found" in result.stdout


# --- logs command additional tests ---

def test_logs_command_with_full_option(elk_api_key, cli_runner):
    """Test logs command with --full option shows detailed output."""
    result = cli_runner.invoke(app, ["logs", "-n", "3", "--full"])

    assert result.exit_code == 0
    assert "Found" in result.stdout
    # Full output shows timestamp and severity in bracket format
    # e.g., [2024-01-01 12:00:00] [INFO ]
    if "No logs found" not in result.stdout:
        assert "[" in result.stdout  # Header format


def test_logs_command_with_raw_option(elk_api_key, cli_runner):
    """Test logs command with --raw option outputs JSON documents."""
    result = cli_runner.invoke(app, ["logs", "-n", "2", "--raw"])

    assert result.exit_code == 0
    assert "Found" in result.stdout
    # Raw output should contain JSON structure
    if "No logs found" not in result.stdout:
        assert "{" in result.stdout
        assert "_source" in result.stdout or "_id" in result.stdout


def test_logs_command_with_service_option(elk_api_key, cli_runner):
    """Test logs command with --service option filters by service name.

    Uses 'backend' service which is consistently active.
    """
    result = cli_runner.invoke(app, ["logs", "-n", "5", "--service", "backend"])

    assert result.exit_code == 0
    assert "service=backend" in result.stdout
    assert "Found" in result.stdout


def test_logs_command_with_service_short_option(elk_api_key, cli_runner):
    """Test logs command with -s short option for service."""
    result = cli_runner.invoke(app, ["logs", "-n", "5", "-s", "dhcpd"])

    assert result.exit_code == 0
    assert "service=dhcpd" in result.stdout


def test_logs_command_with_container_option(elk_api_key, cli_runner):
    """Test logs command with --container option filters by container name.

    Uses 'backend' container which runs in k8s.
    """
    result = cli_runner.invoke(app, ["logs", "-n", "5", "--container", "backend"])

    assert result.exit_code == 0
    assert "container=backend" in result.stdout
    assert "Found" in result.stdout


def test_logs_command_with_container_short_option(elk_api_key, cli_runner):
    """Test logs command with -C short option for container."""
    result = cli_runner.invoke(app, ["logs", "-n", "5", "-C", "backend"])

    assert result.exit_code == 0
    assert "container=backend" in result.stdout


def test_logs_command_with_search_option(elk_api_key, cli_runner):
    """Test logs command with --search option searches message body.

    Searches for 'GET' which is common in HTTP access logs.
    """
    result = cli_runner.invoke(app, ["logs", "-n", "5", "--search", "GET"])

    assert result.exit_code == 0
    assert "search='GET'" in result.stdout
    assert "Found" in result.stdout


def test_logs_command_with_search_short_option(elk_api_key, cli_runner):
    """Test logs command with -S short option for search."""
    result = cli_runner.invoke(app, ["logs", "-n", "5", "-S", "error"])

    assert result.exit_code == 0
    assert "search='error'" in result.stdout


def test_logs_command_with_multiple_filters(elk_api_key, cli_runner):
    """Test logs command with multiple filter options combined."""
    result = cli_runner.invoke(app, [
        "logs", "-n", "5",
        "--service", "backend",
        "--container", "backend",
        "--time", "1h"
    ])

    assert result.exit_code == 0
    assert "service=backend" in result.stdout
    assert "container=backend" in result.stdout
    assert "last 1h" in result.stdout


def test_logs_command_with_nonexistent_service(elk_api_key, cli_runner):
    """Test logs command with non-existent service returns no logs."""
    result = cli_runner.invoke(app, ["logs", "-n", "5", "-s", "nonexistent-service-xyz"])

    assert result.exit_code == 0
    # Should find 0 logs or very few
    assert "Found" in result.stdout or "No logs found" in result.stdout
