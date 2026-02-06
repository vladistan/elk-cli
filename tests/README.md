# elk-tool Test Suite

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures (elk_connection, cli_runner)
├── test_cli.py              # CLI command tests
├── test_client.py           # ELK client tests
├── test_client_utils.py     # Client utility function tests
├── test_exceptions.py       # Exception hierarchy tests
├── test_logging.py          # Logging configuration tests
└── test_monitoring.py       # Sentry integration tests
```

## Running Tests

```bash
# Run all tests
uv run pytest

# With coverage
uv run pytest --cov=src --cov-report=html
```

## Configuration

Tests require a real Elasticsearch instance. Set credentials via environment or `.envrc`:

```bash
export ELK_URL="https://elasticsearch.example.com:9200"
export ELASTIC_API_KEY="your-api-key"  # pragma: allowlist secret
```

The `elk_api_key` fixture discovers credentials from environment variables or `.envrc` files walking up the directory tree.

## Coverage Goals

Target: **65% minimum coverage**

## Writing New Tests

Follow repository testing patterns (CODE-TEST-001, CODE-PY-TEST-001):

- Use functional tests, NOT class-based tests
- NO type annotations in test files
- Never mask failures with conditional assertions
- One concept per test
- Explicit assertions (no `assert result` - be specific)
