# Contributing to elk-tool

Thank you for your interest in contributing to elk-tool! This guide covers development setup, quality standards, and workflows.

## Development Setup

### Prerequisites

- Python 3.11 or higher
- [uv](https://github.com/astral-sh/uv) package manager
- [direnv](https://direnv.net/) (optional, for automatic environment loading)

### Initial Setup

1. **Clone and navigate to elk-tool:**
   ```bash
   cd elk-tool
   ```

2. **Install dependencies:**
   ```bash
   uv sync
   ```

   This creates a virtual environment and installs all runtime and development dependencies.

3. **Configure environment:**

   Create a `.envrc` file for local development:
   ```bash
   export ELK_URL="https://elasticsearch.example.com:9200"
   export ELASTIC_API_KEY="your-api-key-here"  # pragma: allowlist secret
   export ENVIRONMENT="development"
   ```

   **SECURITY WARNING:** Never commit `.envrc` with real credentials. The `.envrc` file should be in `.gitignore`.

4. **Enable direnv (optional):**

   If you use direnv, enable auto-loading:
   ```bash
   direnv allow
   ```

   Otherwise, source your environment manually or export variables directly.

### Running the Tool

```bash
# Run elk-tool commands
uv run elk-tool --help
uv run elk-tool logs --host myserver

# Run arbitrary Python scripts
uv run python -m elk_tool.cli
```

**IMPORTANT:** Always use `uv run` to execute commands. Do NOT use `source .venv/bin/activate` as it is unstable in monorepo environments.

## Quality Standards

elk-tool follows strict quality standards enforced through automated checks and pre-commit hooks.

### Code Quality Tools

- **ruff**: Linting and code formatting
- **mypy**: Static type checking
- **pytest**: Test execution and coverage
- **pre-commit**: Git hook automation

### Running Quality Checks

**During active development (fast feedback):**

```bash
# Stage files first (ensures new files are included)
git add <files-you-edited>

# Run pre-commit on staged files only
pre-commit run --files $(git diff --cached --name-only)
```

**Individual tool commands:**

```bash
# Linting
uv run ruff check src tests          # Check for issues
uv run ruff check --fix src          # Auto-fix issues
uv run ruff format src tests         # Format code

# Type checking
uv run mypy src                      # Type check source only

# Testing
uv run pytest                        # Run all tests
uv run pytest -m unit                # Unit tests only
uv run pytest -m integration         # Integration tests only
uv run pytest -x                     # Stop on first failure
uv run pytest -v                     # Verbose output
uv run pytest --cov=elk_tool         # With coverage report
```

**CRITICAL:** All configured hooks must pass before committing.

### Pre-Commit Hooks

This project uses pre-commit hooks for automated quality checks.

**Hook categories:**
- **File checks**: Large files, merge conflicts, symlinks
- **Format checks**: YAML, JSON, TOML formatting
- **Security checks**: Secret detection (gitleaks, detect-secrets)
- **Code quality**: Python import order, syntax validation

**Install hooks:**
```bash
# From repository root
pre-commit install
```

**Run hooks manually:**
```bash
# On staged files (during development)
pre-commit run --files $(git diff --cached --name-only)

# On all files (before pushing, CI simulation)
pre-commit run --all-files
```

**Note:** In monorepos, `--all-files` can cause slowness. Always use scoped `--files` during active development.

### Test Coverage

- Target: **65%+ coverage**
- Current: **67% coverage** (46 tests passing)

Run coverage report:
```bash
uv run pytest --cov=elk_tool --cov-report=html
open htmlcov/index.html  # View detailed report
```

### Code Style Guidelines

**Documentation philosophy:**
- Code should be self-documenting through clear names and types
- Only add docstrings when:
  - Complex algorithms with non-obvious logic
  - Edge cases or gotchas that need explanation
  - Public API functions used by external users
  - Complex return types where types alone don't convey meaning

**Naming conventions:**
- Functions: `snake_case` (e.g., `get_user_by_id`)
- Classes: `PascalCase` (e.g., `ElkClient`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`)
- Private members: prefix with `_` (e.g., `_internal_helper`)

**Type hints:**
- All functions must have type hints for parameters and return values
- Use `from __future__ import annotations` for forward references
- Avoid `Any` type unless absolutely necessary

## Project Structure

```
elk-tool/
├── src/
│   └── elk_tool/
│       ├── __init__.py
│       ├── application/      # Application logic
│       ├── core/             # Core business logic
│       ├── domain/           # Domain models
│       ├── infra/            # Infrastructure (HTTP, logging)
│       ├── presentation/     # Output formatting
│       └── ui/               # CLI interface
├── tests/
│   ├── application/
│   ├── core/
│   ├── domain/
│   ├── infra/
│   ├── presentation/
│   └── ui/
├── pyproject.toml           # Project config and dependencies
├── README.md                # User documentation
└── CONTRIBUTING.md          # This file
```

### Architecture

elk-tool follows a layered architecture:
- **UI layer**: CLI interface (typer)
- **Application layer**: Orchestration and use cases
- **Core layer**: Business logic
- **Domain layer**: Models and types
- **Infrastructure layer**: External integrations (HTTP, logging, monitoring)
- **Presentation layer**: Output formatting (rich, JSON)

## Dependency Management

```bash
# Add runtime dependency
uv add requests

# Add development dependency
uv add --dev pytest-xdist

# Remove dependency
uv remove requests

# Update all dependencies
uv sync --upgrade

# Install exact versions (CI/production)
uv sync --frozen
```

**IMPORTANT:** Always commit `uv.lock` for reproducible builds.

## Making Contributions

1. **Create a branch** for your changes
2. **Make your changes** following the quality standards above
3. **Stage your files**: `git add <files>`
4. **Run quality checks**: `pre-commit run --files $(git diff --cached --name-only)`
5. **Ensure tests pass**: `uv run pytest`
6. **Commit your changes**: Follow conventional commit format (e.g., `feat:`, `fix:`, `docs:`)
7. **Push and create a pull request**

### Commit Message Format

Follow conventional commits:
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test additions or changes
- `chore:` - Build/tooling changes

Example: `feat: add --format json flag to logs command`

## Getting Help

- Review the [README.md](README.md) for user documentation
- Open an issue on GitHub for questions or bug reports

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) file for details.
