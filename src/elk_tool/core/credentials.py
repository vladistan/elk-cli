"""Elasticsearch credentials and configuration management."""

# Standard library
import logging
import os
import re
from collections.abc import Iterator
from pathlib import Path

# Third-party
from requests import PreparedRequest
from requests.auth import AuthBase

# Local
from elk_tool.core.config import get_profile, load_config, resolve_elk_config
from elk_tool.core.exceptions import ConfigurationError

log = logging.getLogger(__name__)


class ApiKeyAuth(AuthBase):
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def __call__(self, r: PreparedRequest) -> PreparedRequest:
        r.headers["Authorization"] = f"ApiKey {self.api_key}"
        return r


def find_envrc_files() -> Iterator[Path]:
    """Yields .envrc files lazily, walking up from current directory to home.

    Stops at home directory (inclusive) or root if started outside home.
    Files are yielded in local-first order, allowing callers to stop early.
    """
    current = Path.cwd()
    home = Path.home()

    while True:
        envrc = current / ".envrc"
        if envrc.exists():
            yield envrc

        # Stop at home dir or root (whichever comes first)
        if current == home or current == current.parent:
            break

        current = current.parent


def parse_envrc(path: Path) -> dict[str, str]:
    env_vars = {}
    export_pattern = re.compile(r"^export\s+([A-Za-z_][A-Za-z0-9_]*)=(.*)$")

    with path.open() as f:
        for line in f:
            line = line.strip()
            match = export_pattern.match(line)
            if match:
                key = match.group(1)
                value = match.group(2)
                # Remove surrounding quotes if present
                if (value.startswith('"') and value.endswith('"')) or (
                    value.startswith("'") and value.endswith("'")
                ):
                    value = value[1:-1]
                env_vars[key] = value

    return env_vars


def get_envrc_value(key: str) -> str | None:
    """Walks from current directory up to root, stopping when key is found.

    This avoids loading all files unnecessarily.
    """
    envrc_files = find_envrc_files()

    for envrc in envrc_files:
        env_vars = parse_envrc(envrc)
        if key in env_vars:
            return env_vars[key]

    return None


def get_env_value(key: str, default: str | None = None) -> str | None:
    """Priority (highest to lowest):
    1. Environment variables
    2. .envrc files (local directory checked first, walks up only if needed)
    3. Default value
    """
    # First check actual environment
    if key in os.environ:
        return os.environ[key]

    # Then check .envrc chain (local first, stops when found)
    envrc_value = get_envrc_value(key)
    if envrc_value is not None:
        return envrc_value

    return default


def get_elasticsearch_client(profile: str | None = None) -> tuple[str, "ApiKeyAuth"]:
    """Get Elasticsearch client configuration with layered precedence.

    Precedence (highest to lowest):
    1. CLI flags (--profile)
    2. Environment variables (ELK_URL, ELASTIC_API_KEY, ELK_PROFILE)
    3. .envrc files (walks from current directory to home)
    4. Config file (~/.config/elk-tool/config.toml)
    5. Default values

    Raises:
        ConfigurationError: If no API key is found in any source.
    """
    # Load config file and select profile
    app_config = load_config()
    elk_profile = get_profile(app_config, profile)

    # Get env/envrc values (may be None)
    env_url = get_env_value("ELK_URL")
    env_api_key = get_env_value("ELASTIC_API_KEY")
    env_username = get_env_value("ELK_USERNAME")
    env_password = get_env_value("ELK_PASSWORD")

    # Resolve with precedence
    resolved = resolve_elk_config(
        config=elk_profile,
        env_url=env_url,
        env_api_key=env_api_key,
        env_username=env_username,
        env_password=env_password,
    )

    # Validate auth credentials exist
    if not resolved["api_key"] and not (resolved["username"] and resolved["password"]):
        log.debug("No authentication credentials found in environment, .envrc, or config file")
        raise ConfigurationError(
            "No authentication credentials found. Set ELASTIC_API_KEY in environment/config, "
            "or set ELK_USERNAME and ELK_PASSWORD."
        )

    # Use API key auth if available
    if resolved["api_key"]:
        log.debug("Using ELK URL: %s (with API key auth)", resolved["url"])
        return resolved["url"], ApiKeyAuth(resolved["api_key"])

    # Fall back to basic auth (not yet implemented, but config supports it)
    log.debug("Using ELK URL: %s (with basic auth)", resolved["url"])
    raise ConfigurationError("Basic auth not yet implemented. Use ELASTIC_API_KEY.")
