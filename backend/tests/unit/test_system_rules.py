"""Tests for system rules service."""

import json
import tempfile
from pathlib import Path

from text_to_sql.services.system_rules import (
    EXCLUDED_SELECT_COLUMNS,
    SystemRulesService,
    get_system_rules_service,
)


class TestExcludedSelectColumns:
    """Test EXCLUDED_SELECT_COLUMNS constant."""

    def test_contains_expected_columns(self):
        """Test that the constant contains all expected system columns."""
        expected = {"sysId", "deletedAt", "createdAt", "updatedAt"}
        assert expected == EXCLUDED_SELECT_COLUMNS

    def test_is_frozenset(self):
        """Test that the constant is a frozenset (immutable)."""
        assert isinstance(EXCLUDED_SELECT_COLUMNS, frozenset)


class TestSystemRulesService:
    """Test SystemRulesService class."""

    def test_load_default_rules(self):
        """Test loading rules from default path."""
        service = get_system_rules_service()
        assert service.rules is not None
        assert "soft_delete" in service.rules

    def test_format_for_prompt_includes_soft_delete(self):
        """Test that format_for_prompt includes soft delete rule."""
        service = get_system_rules_service()
        prompt = service.format_for_prompt()

        assert "SOFT DELETE" in prompt
        assert "deletedAt IS NULL" in prompt

    def test_format_for_prompt_includes_excluded_columns(self):
        """Test that format_for_prompt includes excluded columns rule."""
        service = get_system_rules_service()
        prompt = service.format_for_prompt()

        assert "EXCLUDED SELECT COLUMNS" in prompt
        assert "sysId" in prompt
        assert "deletedAt" in prompt
        assert "createdAt" in prompt
        assert "updatedAt" in prompt
        assert "Do NOT include these columns in SELECT" in prompt

    def test_format_for_prompt_with_custom_rules(self):
        """Test format_for_prompt with custom rules file."""
        rules = {
            "soft_delete": {
                "description": "Test soft delete",
                "rule": "Filter by deletedAt",
            },
            "excluded_select_columns": {
                "description": "System columns to exclude",
                "columns": ["col1", "col2"],
                "rule": "Do not include in SELECT",
            },
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rules, f)
            f.flush()
            temp_path = f.name

        try:
            service = SystemRulesService(temp_path)
            prompt = service.format_for_prompt()

            assert "EXCLUDED SELECT COLUMNS" in prompt
            assert "col1, col2" in prompt
            assert "Do not include in SELECT" in prompt
        finally:
            Path(temp_path).unlink()

    def test_format_for_prompt_empty_rules(self):
        """Test format_for_prompt with empty rules."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({}, f)
            f.flush()
            temp_path = f.name

        try:
            service = SystemRulesService(temp_path)
            prompt = service.format_for_prompt()
            assert prompt == ""
        finally:
            Path(temp_path).unlink()

    def test_format_for_prompt_missing_file(self):
        """Test format_for_prompt when rules file doesn't exist."""
        service = SystemRulesService("/nonexistent/path/rules.json")
        prompt = service.format_for_prompt()
        assert prompt == ""
