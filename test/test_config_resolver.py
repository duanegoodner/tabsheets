"""Tests for ConfigResolver."""
import pytest
from pathlib import Path

from tabsheets.config_resolver import ConfigResolver


class TestConfigResolver:
    """Test configuration resolution logic."""

    def test_resolve_from_config_only(self):
        """Test resolving a value from config only."""
        config = {"table_path": "/path/to/table.md"}
        resolver = ConfigResolver(config)
        
        result = resolver.resolve("table_path", None, is_path=True)
        assert result == "/path/to/table.md"

    def test_resolve_from_cli_only(self):
        """Test resolving a value from CLI only."""
        config = {}
        resolver = ConfigResolver(config)
        
        result = resolver.resolve("table_path", Path("/cli/path.md"), is_path=True)
        assert result == Path("/cli/path.md")

    def test_resolve_matching_values(self):
        """Test resolving when CLI and config match."""
        config = {"table_path": "/path/to/table.md"}
        resolver = ConfigResolver(config)
        
        result = resolver.resolve("table_path", Path("/path/to/table.md"), is_path=True)
        assert result == Path("/path/to/table.md")

    def test_resolve_conflicting_values_raises_error(self):
        """Test that conflicting values raise an error."""
        config = {"table_path": "/config/path.md"}
        resolver = ConfigResolver(config)
        
        with pytest.raises(ValueError, match="Conflict for 'table_path'"):
            resolver.resolve("table_path", Path("/cli/path.md"), is_path=True)

    def test_resolve_missing_required_raises_error(self):
        """Test that missing required field raises an error."""
        config = {}
        resolver = ConfigResolver(config)
        
        with pytest.raises(ValueError, match="Missing required field"):
            resolver.resolve("table_path", None, required=True)

    def test_resolve_missing_optional_returns_none(self):
        """Test that missing optional field returns None."""
        config = {}
        resolver = ConfigResolver(config)
        
        result = resolver.resolve("optional_field", None, required=False)
        assert result is None

    def test_resolve_string_values(self):
        """Test resolving non-path string values."""
        config = {"sheet_title": "My Sheet"}
        resolver = ConfigResolver(config)
        
        result = resolver.resolve("sheet_title", None)
        assert result == "My Sheet"

    def test_resolve_string_conflict(self):
        """Test string value conflicts are detected."""
        config = {"sheet_title": "Config Title"}
        resolver = ConfigResolver(config)
        
        with pytest.raises(ValueError, match="Conflict for 'sheet_title'"):
            resolver.resolve("sheet_title", "CLI Title")
