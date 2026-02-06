import os

import pytest
from typer.testing import CliRunner

from elk_tool.core.client import ElkClient
from elk_tool.core.credentials import ApiKeyAuth, get_env_value

DEFAULT_ELK_URL = "https://elasticsearch.example.com:9200"


@pytest.fixture(scope="session")
def elk_api_key():
    api_key = get_env_value("ELASTIC_API_KEY")
    if not api_key:
        pytest.fail(
            "ELASTIC_API_KEY not found. Set it as environment variable or in .envrc file. "
            "Integration tests require ELK credentials to run."
        )
    return api_key


@pytest.fixture(scope="session")
def elk_url():
    return os.getenv("ELK_URL", DEFAULT_ELK_URL)


@pytest.fixture(scope="session")
def elk_client(elk_api_key, elk_url):
    auth = ApiKeyAuth(elk_api_key)
    return ElkClient(elk_url, auth)


@pytest.fixture
def cli_runner():
    return CliRunner()
