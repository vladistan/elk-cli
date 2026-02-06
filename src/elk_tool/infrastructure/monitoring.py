"""Sentry monitoring integration for elk-tool."""

import sentry_sdk

from elk_tool import __version__


def setup_sentry(environment: str = "local") -> None:
    """DSN is hardcoded per repository patterns. Samples 3% of transactions."""
    sentry_sdk.init(
        dsn="https://d6fcfe8a4373a10a5df6ea8ba5dac756@o4508594232426496.ingest.us.sentry.io/4510802947145728",
        traces_sample_rate=0.03,
        environment=environment,
        release=__version__,
        attach_stacktrace=True,
        send_default_pii=False,
    )
