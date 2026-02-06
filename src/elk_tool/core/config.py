"""Configuration management for elk-tool.

Loads configuration from multiple sources with layered precedence:
1. CLI flags (--profile)
2. Environment variables (ELK_PROFILE, ELK_URL, etc.)
3. Config file (~/.config/elk-tool/config.toml)
4. Default values (lowest priority)
"""

import os
import tomllib
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from elk_tool.core.exceptions import ConfigurationError


class ElkProfile(BaseModel):

    url: str = Field(
        default="https://elasticsearch.example.com:9200",
        description="Elasticsearch endpoint URL",
    )
    api_key: str | None = Field(
        default=None,
        description="API key for authentication",
    )
    username: str | None = Field(
        default=None,
        description="Username for basic authentication",
    )
    password: str | None = Field(
        default=None,
        description="Password for basic authentication",
    )
    timeout: int = Field(
        default=30,
        description="Request timeout in seconds",
    )
    verify_tls: bool = Field(
        default=True,
        description="Verify TLS certificates",
    )


class AppConfig(BaseModel):

    default_profile: str = Field(default="default")
    profiles: dict[str, ElkProfile] = Field(
        default_factory=lambda: {"default": ElkProfile()}
    )


def load_config(config_path: Path | None = None) -> AppConfig:
    """Load from TOML file with legacy [elk] format support.

    Search order: explicit path > ~/.config/elk-tool/config.toml > defaults.
    """
    search_paths = [
        Path.home() / ".config" / "elk-tool" / "config.toml",
    ]

    if config_path:
        search_paths.insert(0, config_path)

    for path in search_paths:
        if path.exists():
            with path.open("rb") as f:
                config_data = tomllib.load(f)
                # Legacy format: convert [elk] to default profile
                if "elk" in config_data and "profiles" not in config_data:
                    config_data = {
                        "default_profile": "default",
                        "profiles": {"default": config_data["elk"]},
                    }
                return AppConfig(**config_data)

    # No config file found, return defaults
    return AppConfig()


def get_profile(config: AppConfig, profile: str | None = None) -> ElkProfile:
    """Select a profile with environment variable fallback.

    Resolution order: explicit profile > ELK_PROFILE env > config default
    """
    profile_name = profile or os.environ.get("ELK_PROFILE") or config.default_profile

    if profile_name not in config.profiles:
        available = ", ".join(sorted(config.profiles.keys()))
        raise ConfigurationError(
            f"Profile '{profile_name}' not found. "
            f"Available profiles: {available}"
        )

    return config.profiles[profile_name]


def resolve_elk_config(
    config: ElkProfile,
    env_url: str | None = None,
    env_api_key: str | None = None,
    env_username: str | None = None,
    env_password: str | None = None,
) -> dict[str, Any]:
    """Merge profile config with environment variable overrides."""
    return {
        "url": env_url if env_url is not None else config.url,
        "api_key": env_api_key if env_api_key is not None else config.api_key,
        "username": env_username if env_username is not None else config.username,
        "password": env_password if env_password is not None else config.password,
        "timeout": config.timeout,
        "verify_tls": config.verify_tls,
    }
