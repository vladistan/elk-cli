"""Unit tests for elk_tool.credentials module."""

import os
import types
from pathlib import Path

import pytest

from elk_tool.core.credentials import ApiKeyAuth, find_envrc_files, get_env_value, parse_envrc


@pytest.fixture
def home_subdir_with_envrc():
    """Create a temporary directory inside home with .envrc for testing.

    Yields the path to the test subdirectory, then cleans up.
    """
    home = Path.home()
    test_subdir = home / ".elk-tool-test-temp"
    test_subdir.mkdir(exist_ok=True)
    envrc_file = test_subdir / ".envrc"
    envrc_file.write_text("export TEST=1")

    yield test_subdir

    # Cleanup
    envrc_file.unlink(missing_ok=True)
    test_subdir.rmdir()


def test_api_key_auth():
    """Test ApiKeyAuth sets correct header."""
    auth = ApiKeyAuth("test-api-key")

    # Create a mock request object
    class MockRequest:
        def __init__(self):
            self.headers = {}

    request = MockRequest()
    result = auth(request)

    assert result.headers["Authorization"] == "ApiKey test-api-key"


def test_parse_envrc_with_exports(tmp_path):
    """Test parsing .envrc file with export statements."""
    envrc = tmp_path / ".envrc"
    envrc.write_text(
        'export API_KEY="secret123"\n' 'export URL=http://localhost:9200\n' "export NAME=test\n"
    )

    env_vars = parse_envrc(envrc)

    assert env_vars["API_KEY"] == "secret123"
    assert env_vars["URL"] == "http://localhost:9200"
    assert env_vars["NAME"] == "test"


def test_parse_envrc_with_quoted_values(tmp_path):
    """Test that parse_envrc handles single and double quotes."""
    envrc = tmp_path / ".envrc"
    envrc.write_text('export VAR1="value1"\n' "export VAR2='value2'\n" "export VAR3=value3\n")

    env_vars = parse_envrc(envrc)

    assert env_vars["VAR1"] == "value1"
    assert env_vars["VAR2"] == "value2"
    assert env_vars["VAR3"] == "value3"


def test_parse_envrc_ignores_non_export_lines(tmp_path):
    """Test that parse_envrc ignores comments and other lines."""
    envrc = tmp_path / ".envrc"
    envrc.write_text(
        "# This is a comment\n"
        'export KEY1="value1"\n'
        "some other line\n"
        'export KEY2="value2"\n'
    )

    env_vars = parse_envrc(envrc)

    assert len(env_vars) == 2
    assert env_vars["KEY1"] == "value1"
    assert env_vars["KEY2"] == "value2"


def test_find_envrc_files_empty_when_none_exist(tmp_path, monkeypatch):
    """Test find_envrc_files yields nothing when no .envrc files exist."""
    monkeypatch.chdir(tmp_path)
    files = list(find_envrc_files())
    assert files == []


def test_find_envrc_files_finds_in_current_dir(tmp_path, monkeypatch):
    """Test find_envrc_files yields .envrc in current directory."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".envrc").write_text("export TEST=1")

    files = list(find_envrc_files())

    assert len(files) == 1
    assert files[0].name == ".envrc"


def test_find_envrc_files_walks_up_directory_tree(tmp_path, monkeypatch):
    """Test find_envrc_files walks up directory tree in order."""
    # Create nested structure: tmp/parent/.envrc and tmp/parent/child/.envrc
    parent = tmp_path / "parent"
    child = parent / "child"
    child.mkdir(parents=True)

    (parent / ".envrc").write_text("export PARENT=1")
    (child / ".envrc").write_text("export CHILD=1")

    monkeypatch.chdir(child)
    files = list(find_envrc_files())

    # Should find child first, then parent (local-first order)
    assert len(files) == 2
    assert files[0].parent == child
    assert files[1].parent == parent


def test_find_envrc_files_is_lazy_generator(tmp_path, monkeypatch):
    """Test find_envrc_files is a generator that yields lazily."""
    (tmp_path / ".envrc").write_text("export TEST=1")
    monkeypatch.chdir(tmp_path)

    result = find_envrc_files()

    # Should be a generator, not a list
    assert isinstance(result, types.GeneratorType)


def test_find_envrc_files_stops_at_home(home_subdir_with_envrc, monkeypatch):
    """Test find_envrc_files stops at home directory."""
    test_subdir = home_subdir_with_envrc
    home = Path.home()

    monkeypatch.chdir(test_subdir)
    files = list(find_envrc_files())

    # Should find .envrc in test_subdir
    assert len(files) >= 1
    assert files[0] == test_subdir / ".envrc"

    # Should not go above home - verify no paths above home
    for f in files:
        # All found files should be at or under home
        assert str(f).startswith(str(home))


def test_get_env_value_from_environment():
    """Test that get_env_value prioritizes actual environment variables."""
    os.environ["TEST_VAR_123"] = "from_env"

    value = get_env_value("TEST_VAR_123")

    assert value == "from_env"

    # Cleanup
    del os.environ["TEST_VAR_123"]


def test_get_env_value_returns_default_when_not_found():
    """Test that get_env_value returns default when variable not found."""
    value = get_env_value("NONEXISTENT_VAR_XYZ", default="default_value")
    assert value == "default_value"


def test_get_env_value_returns_none_when_no_default():
    """Test that get_env_value returns None when no default and not found."""
    value = get_env_value("NONEXISTENT_VAR_ABC")
    assert value is None
