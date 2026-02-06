"""Test command implementations for verifying integrations."""

import typer

from elk_tool import __version__


def run_sentry_test() -> None:
    # Local import: sentry_sdk only needed for this test command
    import sentry_sdk

    typer.echo("Sending test error to Sentry...")

    try:
        raise RuntimeError("elk-tool Sentry test error")
    except RuntimeError:
        sentry_sdk.capture_exception()

    typer.echo("Sending test transaction with spans...")

    with sentry_sdk.start_transaction(op="test", name="elk-tool-test") as txn:
        txn.set_tag("test", "true")
        with sentry_sdk.start_span(op="parent", description="Parent span"):
            sentry_sdk.start_span(op="child", description="Child span").finish()

    typer.echo("Flushing to Sentry...")
    sentry_sdk.flush(timeout=5)

    typer.echo("\nDone! Please verify in Sentry console:")
    typer.echo("  1. Issues: Look for 'elk-tool Sentry test error'")
    typer.echo("  2. Performance: Look for 'elk-tool-test' transaction")
    typer.echo(f"  3. Check environment='local', release='{__version__}'")
