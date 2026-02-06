# elk-tool

Command-line interface for querying and managing Elasticsearch data. Designed for operators and developers who need fast access to logs, metrics, and cluster information from the terminal.

## Features

- **Log querying** with smart filtering (host, service, severity, time range, text search)
- **Document operations** (lift, delete, list, cleanup test data)
- **Cluster management** (health checks, shard status, index listing)
- **Multiple output formats** (table, JSON, raw)
- **Pipeline-friendly** (clean stdout/stderr separation)
- **Type-safe** Python implementation with comprehensive error handling

## Installation

Requirements: Python 3.11+, [uv](https://github.com/astral-sh/uv)

```bash
# Clone repository or navigate to elk-tool directory
cd elk-tool

# Install dependencies
uv sync

# Verify installation
uv run elk-tool --help
```

## Configuration

elk-tool uses layered configuration with the following precedence (highest to lowest):

1. **CLI flags** (`--profile`) — override everything
2. **Environment variables** (`ELK_PROFILE`, `ELK_URL`, etc.) — per-session overrides
3. **Config file** (`~/.config/elk-tool/config.toml`) — persistent settings
4. **Built-in defaults** — fallback values

### Config File

Create `~/.config/elk-tool/config.toml` from the included example:

```bash
mkdir -p ~/.config/elk-tool
cp config.example.toml ~/.config/elk-tool/config.toml
```

The config file supports multiple named profiles:

```toml
default_profile = "default"

[profiles.default]
url = "https://elasticsearch.example.com:9200"
api_key = "your-api-key-here"  # pragma: allowlist secret
timeout = 30
verify_tls = true

[profiles.production]
url = "https://elk-prod.example.com:9200"
api_key = "prod-api-key"  # pragma: allowlist secret
timeout = 60

[profiles.local]
url = "http://localhost:9200"
verify_tls = false
```

See [config.example.toml](config.example.toml) for all available settings.

### Profile Selection

Switch between profiles using `--profile` or the `ELK_PROFILE` environment variable:

```bash
# Use a named profile
uv run elk-tool --profile production logs -t 1h

# Set default profile via environment variable
export ELK_PROFILE="production"
uv run elk-tool logs -t 1h

# CLI flag takes precedence over environment variable
ELK_PROFILE=production uv run elk-tool --profile local logs
```

Profile resolution order: `--profile` flag > `ELK_PROFILE` env var > `default_profile` from config > built-in default.

### Environment Variables

Environment variables override config file and profile values:

```bash
# Elasticsearch endpoint (overrides profile URL)
export ELK_URL="https://elasticsearch.example.com:9200"

# API Key authentication (preferred, overrides profile)
export ELASTIC_API_KEY="your-api-key-here"  # pragma: allowlist secret

# Basic auth (alternative to API key)
export ELK_USERNAME="elastic"
export ELK_PASSWORD="changeme"  # pragma: allowlist secret

# Profile selection
export ELK_PROFILE="production"

# Optional settings
export ENVIRONMENT="production"   # Environment tag for Sentry (default: local)
```

### Example .envrc (for direnv users)

```bash
export ELK_URL="https://elasticsearch.example.com:9200"
export ELASTIC_API_KEY="your-api-key"  # pragma: allowlist secret
export ELK_PROFILE="default"
export ENVIRONMENT="local"
```

## Usage Examples

### Viewing Logs

```bash
# Recent logs (last 20)
uv run elk-tool logs

# Logs from specific time range
uv run elk-tool logs -t 15m          # Last 15 minutes
uv run elk-tool logs -t 1h           # Last hour
uv run elk-tool logs -t 24h          # Last 24 hours
uv run elk-tool logs -t 7d           # Last week

# Filter by host, service, or container
uv run elk-tool logs -h firewall7
uv run elk-tool logs -s litellm
uv run elk-tool logs -C sentry-nginx-1

# Combine filters
uv run elk-tool logs -h sentry -C pgbouncer -t 1h

# Filter by severity level
uv run elk-tool logs -l error        # ERROR and FATAL only
uv run elk-tool logs -l warn         # WARN, ERROR, FATAL

# Search text in log messages
uv run elk-tool logs -S "connection refused" -t 1h

# Custom columns
uv run elk-tool logs -c ts,level,id,msg

# Raw JSON output (for piping)
uv run elk-tool logs --raw | jq '.hits.hits[]._source'
```

### Document Operations

```bash
# Lift (retrieve) a document
uv run elk-tool lift logs-generic.otel-default DOC_ID

# Lift and save to file
uv run elk-tool lift INDEX DOC_ID -o testdata/

# Lift just the message body
uv run elk-tool lift INDEX DOC_ID -r

# Delete a document
uv run elk-tool delete INDEX DOC_ID

# Delete without confirmation
uv run elk-tool delete INDEX DOC_ID --force

# List recent documents
uv run elk-tool list INDEX
uv run elk-tool list INDEX --size 50
uv run elk-tool list INDEX --full    # Show full document source

# Clean up test documents (marked with int-test: true)
uv run elk-tool cleanup INDEX --dry-run
uv run elk-tool cleanup INDEX
```

### Cluster Operations

```bash
# Show cluster health
uv run elk-tool cluster-health

# Show shard status and diagnose allocation issues
uv run elk-tool shard-status
uv run elk-tool shard-status --explain

# List indices
uv run elk-tool indices
uv run elk-tool indices 'logs-*'

# List data streams
uv run elk-tool indices --data-streams

# Show field mappings
uv run elk-tool mapping
uv run elk-tool mapping -f attributes.net
uv run elk-tool mapping --raw
```

### Discovery Commands

```bash
# List all hosts sending data
uv run elk-tool hosts
uv run elk-tool hosts -t 1h          # Last hour
uv run elk-tool hosts -s myservice   # Filter by service

# List all services
uv run elk-tool services
uv run elk-tool services -t 24h      # Last 24 hours
uv run elk-tool services -h myhost   # Filter by host
```

### Raw Queries

```bash
# Execute raw Elasticsearch query
uv run elk-tool query '{"query": {"match_all": {}}}' -n 10

# Aggregation query
uv run elk-tool query '{"size": 0, "aggs": {"hosts": {"terms": {"field": "host.name"}}}}' -i logs-*

# Raw JSON output
uv run elk-tool query '{"query": {"match_all": {}}}' --raw
```

## Commands Reference

### Log and Metric Commands
- `logs` - View logs with smart filtering (host, service, container, severity, time, search)
- `hosts` - List unique hostnames in logs or metrics stream
- `services` - List unique services in logs or metrics stream

### Document Commands
- `lift` - Retrieve a document by ID (with optional save-to-file and delete-after)
- `delete` - Delete a document by ID
- `list` - List recent documents in an index
- `cleanup` - Delete test documents marked with `int-test: true`

### Cluster Commands
- `cluster-health` - Show cluster health and node status
- `shard-status` - Show unassigned shards and allocation issues
- `indices` - List indices and data streams
- `mapping` - Show field mappings for an index

### Raw Query Commands
- `query` - Execute raw Elasticsearch query JSON

### Test Commands
- `test sentry` - Send test error and transaction to Sentry

## Output Modes

Most commands support multiple output formats:

- **Table mode** (default): Human-readable tables with Rich formatting
- **Full mode** (`--full`): Expanded view with complete document details
- **Raw mode** (`--raw`): JSON output for piping to `jq` or other tools

## Exit Codes

elk-tool uses standard exit codes for scripting:

- `0` - Success
- `1` - General error
- `2` - Usage error (invalid arguments)
- `3` - Input error (file not found, bad data)
- `4` - Output error (cannot write file)
- `5` - Network error (connection failed)
- `6` - Timeout

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for developer setup, testing, and contribution guidelines.

## License

MIT
