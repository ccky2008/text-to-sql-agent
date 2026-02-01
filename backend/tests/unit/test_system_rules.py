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


class TestKeyValueSearchRule:
    """Test key_value_search rule formatting."""

    def test_format_for_prompt_includes_key_value_search(self):
        """Test that format_for_prompt includes key_value_search rule."""
        service = get_system_rules_service()
        prompt = service.format_for_prompt()

        assert "KEY_VALUE SEARCH" in prompt
        assert "case-insensitive" in prompt.lower()

    def test_format_for_prompt_includes_key_value_examples(self):
        """Test that format_for_prompt includes key_value_search examples."""
        service = get_system_rules_service()
        prompt = service.format_for_prompt()

        assert "LOWER(kv.\"key\")" in prompt
        assert "ILIKE" in prompt


class TestTagAggregationRule:
    """Test tag_aggregation rule formatting."""

    def test_format_for_prompt_includes_tag_aggregation(self):
        """Test that format_for_prompt includes tag_aggregation rule."""
        service = get_system_rules_service()
        prompt = service.format_for_prompt()

        assert "TAG AGGREGATION" in prompt
        assert "NEVER output generic 'TAG_KEY' or 'TAG_VALUE'" in prompt

    def test_format_for_prompt_includes_tag_aggregation_patterns(self):
        """Test that format_for_prompt includes tag_aggregation SQL patterns."""
        service = get_system_rules_service()
        prompt = service.format_for_prompt()

        assert "Patterns:" in prompt
        assert "tag_as_column" in prompt
        assert "MAX(CASE WHEN" in prompt
        assert "STRING_AGG" in prompt

    def test_format_for_prompt_includes_tag_aggregation_examples(self):
        """Test that format_for_prompt includes tag_aggregation examples."""
        service = get_system_rules_service()
        prompt = service.format_for_prompt()

        assert "Examples:" in prompt
        assert "Environment" in prompt

    def test_format_for_prompt_with_custom_tag_aggregation(self):
        """Test format_for_prompt with custom tag_aggregation rule."""
        rules = {
            "tag_aggregation": {
                "description": "Test tag aggregation",
                "rule": "Use MAX CASE for pivoting",
                "patterns": {
                    "test_pattern": "MAX(CASE WHEN key = 'x' THEN val END)"
                },
                "examples": [
                    "Example: pivot Environment tag"
                ]
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(rules, f)
            f.flush()
            temp_path = f.name

        try:
            service = SystemRulesService(temp_path)
            prompt = service.format_for_prompt()

            assert "TAG AGGREGATION: Test tag aggregation" in prompt
            assert "Rule: Use MAX CASE for pivoting" in prompt
            assert "Patterns:" in prompt
            assert "test_pattern: MAX(CASE WHEN key = 'x' THEN val END)" in prompt
            assert "Examples:" in prompt
            assert "Example: pivot Environment tag" in prompt
        finally:
            Path(temp_path).unlink()
