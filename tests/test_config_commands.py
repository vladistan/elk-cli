import json
from unittest.mock import patch

import pytest
import requests as req_lib
from typer.testing import CliRunner

from elk_tool.core.config import AppConfig, ElkProfile
from elk_tool.ui.cli import app
from elk_tool.ui.commands.config import mask_secret

runner = CliRunner()


def _make_config(profiles=None, default="ars"):
    if profiles is None:
        profiles = {
            "ars": ElkProfile(
                url="https://c868c2d4.example.es.io",
                api_key="test-key-ars-1234",  # pragma: allowlist secret
            ),
            "r4": ElkProfile(
                url="https://elk2-1.r4.example.com",
                api_key="test-key-r4-5678",  # pragma: allowlist secret
                username="admin",
                password="test-pass-9012",  # noqa: S106  # pragma: allowlist secret
            ),
        }
    return AppConfig(default_profile=default, profiles=profiles)



@pytest.mark.parametrize(
    "value,expected",
    [
        (None, "—"),
        ("", "—"),
        ("abc", "***"),
        ("abcd", "***"),
        ("test-key-ars-1234", "***...1234"),  # pragma: allowlist secret
        ("test-pass-9012", "***...9012"),  # pragma: allowlist secret
    ],
)
def test_mask_secret(value, expected):
    assert mask_secret(value) == expected


@patch("elk_tool.ui.commands.config.load_config")
def test_profiles_table(mock_load):
    mock_load.return_value = _make_config()
    result = runner.invoke(app, ["config", "profiles"])

    assert result.exit_code == 0
    assert "ars" in result.stdout
    assert "r4" in result.stdout
    assert "*" in result.stdout


@patch("elk_tool.ui.commands.config.load_config")
def test_profiles_json(mock_load):
    mock_load.return_value = _make_config()
    result = runner.invoke(app, ["config", "profiles", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 2
    assert data[0]["name"] == "ars"
    assert data[0]["default"] == "*"
    assert data[1]["name"] == "r4"
    assert data[1]["default"] == ""


@patch("elk_tool.ui.commands.config.load_config")
def test_profiles_empty(mock_load):
    mock_load.return_value = AppConfig(profiles={})
    result = runner.invoke(app, ["config", "profiles"])

    assert result.exit_code == 0
    assert "No profiles configured" in result.stdout


@patch("elk_tool.ui.commands.config.load_config")
def test_show_table(mock_load):
    mock_load.return_value = _make_config()
    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "ars" in result.stdout
    assert "r4" in result.stdout
    # API keys should be masked
    assert "test-key-ars-1234" not in result.stdout
    assert "***...1234" in result.stdout


@patch("elk_tool.ui.commands.config.load_config")
def test_show_json(mock_load):
    mock_load.return_value = _make_config()
    result = runner.invoke(app, ["config", "show", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 2
    assert data[0]["api_key"] == "***...1234"
    assert data[1]["password"] == "***...9012"  # noqa: S105
    assert data[1]["username"] == "admin"


@patch("elk_tool.ui.commands.config.load_config")
def test_show_masks_password(mock_load):
    mock_load.return_value = _make_config()
    result = runner.invoke(app, ["config", "show"])

    assert result.exit_code == 0
    assert "test-pass-9012" not in result.stdout


@patch("elk_tool.ui.commands.config.requests.get")
@patch("elk_tool.ui.commands.config.load_config")
def test_validate_ok(mock_load, mock_get):
    mock_load.return_value = _make_config()
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status.return_value = None
    mock_get.return_value.json.return_value = {"cluster_name": "test-cluster"}

    result = runner.invoke(app, ["config", "validate"])

    assert result.exit_code == 0
    assert "OK" in result.stdout
    assert "test-cluster" in result.stdout


@patch("elk_tool.ui.commands.config.requests.get")
@patch("elk_tool.ui.commands.config.load_config")
def test_validate_fail(mock_load, mock_get):
    mock_load.return_value = _make_config()
    mock_get.side_effect = req_lib.ConnectionError("Connection refused")

    result = runner.invoke(app, ["config", "validate"])

    assert result.exit_code == 1
    assert "FAIL" in result.stdout
    assert "Connection refused" in result.stdout


@patch("elk_tool.ui.commands.config.requests.get")
@patch("elk_tool.ui.commands.config.load_config")
def test_validate_mixed(mock_load, mock_get):
    mock_load.return_value = _make_config()

    ok_response = type("Response", (), {
        "status_code": 200,
        "raise_for_status": lambda self: None,
        "json": lambda self: {"cluster_name": "prod"},
    })()

    def side_effect(url, **kwargs):
        if "c868c2d4" in url:
            return ok_response
        raise req_lib.ConnectionError("timeout")

    mock_get.side_effect = side_effect

    result = runner.invoke(app, ["config", "validate"])

    assert result.exit_code == 1
    assert "OK" in result.stdout
    assert "FAIL" in result.stdout


@patch("elk_tool.ui.commands.config.requests.get")
@patch("elk_tool.ui.commands.config.load_config")
def test_validate_json(mock_load, mock_get):
    mock_load.return_value = _make_config()
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status.return_value = None
    mock_get.return_value.json.return_value = {"cluster_name": "test-cluster"}

    result = runner.invoke(app, ["config", "validate", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert len(data) == 2
    assert all(r["status"] == "OK" for r in data)


@patch("elk_tool.ui.commands.config.requests.get")
@patch("elk_tool.ui.commands.config.load_config")
def test_validate_uses_api_key_header(mock_load, mock_get):
    mock_load.return_value = _make_config(
        profiles={"test": ElkProfile(url="https://es.example.com", api_key="elk-validate-7890")}  # pragma: allowlist secret
    )
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status.return_value = None
    mock_get.return_value.json.return_value = {"cluster_name": "c"}

    runner.invoke(app, ["config", "validate"])

    call_kwargs = mock_get.call_args
    assert call_kwargs.kwargs["headers"]["Authorization"] == "ApiKey elk-validate-7890"  # pragma: allowlist secret


@patch("elk_tool.ui.commands.config.requests.get")
@patch("elk_tool.ui.commands.config.load_config")
def test_validate_uses_basic_auth(mock_load, mock_get):
    mock_load.return_value = _make_config(
        profiles={
            "test": ElkProfile(
                url="https://es.example.com",
                username="admin",
                password="test-auth-4321",  # noqa: S106  # pragma: allowlist secret
            )
        }
    )
    mock_get.return_value.status_code = 200
    mock_get.return_value.raise_for_status.return_value = None
    mock_get.return_value.json.return_value = {"cluster_name": "c"}

    runner.invoke(app, ["config", "validate"])

    call_kwargs = mock_get.call_args
    assert call_kwargs.kwargs["auth"] == ("admin", "test-auth-4321")  # pragma: allowlist secret
