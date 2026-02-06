"""Basic CLI smoke tests."""

from elk_tool.ui.cli import app


def test_cli_help(cli_runner):
    result = cli_runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "ELK Tool" in result.stdout
    assert "Query and manage Elasticsearch data" in result.stdout


def test_cli_version(cli_runner):
    result = cli_runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert "elk-tool" in result.stdout.lower()


def test_cluster_health_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["cluster-health"])

    assert result.exit_code == 0
    assert "Status" in result.stdout or "status" in result.stdout


def test_indices_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["indices"])

    assert result.exit_code == 0
    assert len(result.stdout) > 0


def test_lift_document_not_found(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["lift", "logs-*", "nonexistent-id"])

    assert result.exit_code != 0
    assert result.exception
    assert "not found" in str(result.exception).lower()


def test_test_sentry_command(cli_runner):
    result = cli_runner.invoke(app, ["test", "sentry"])

    assert result.exit_code == 0


def test_invalid_command(cli_runner):
    result = cli_runner.invoke(app, ["invalid-command"])

    assert result.exit_code != 0


def test_mapping_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["mapping", "logs-*"])

    assert result.exit_code == 0


def test_logs_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["logs", "-n", "5"])

    assert result.exit_code == 0


def test_query_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["query", '{"query":{"match_all":{}},"size":1}'])

    assert result.exit_code == 0


def test_hosts_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["hosts"])

    assert result.exit_code == 0


def test_services_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["services"])

    assert result.exit_code == 0


def test_shard_status_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["shard-status"])

    assert result.exit_code == 0


def test_list_command(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["list", "logs-*", "-n", "5"])

    assert result.exit_code == 0


def test_logs_with_filters(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, ["logs", "-t", "1h", "-n", "5"])
    assert result.exit_code == 0

    result = cli_runner.invoke(app, ["logs", "-l", "error", "-n", "5"])
    assert result.exit_code == 0


def test_query_with_index_option(elk_api_key, cli_runner):
    result = cli_runner.invoke(app, [
        "query",
        '{"query":{"match_all":{}},"size":1}',
        "--index", "logs-*"
    ])

    assert result.exit_code == 0


def test_cli_verbose_flag(cli_runner):
    result = cli_runner.invoke(app, ["--verbose", "--help"])
    assert result.exit_code == 0
