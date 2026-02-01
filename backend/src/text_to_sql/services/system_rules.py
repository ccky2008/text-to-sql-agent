"""System rules configuration service."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

EXCLUDED_SELECT_COLUMNS: frozenset[str] = frozenset({
    "sysId",
    "deletedAt",
    "createdAt",
    "updatedAt",
})


class SystemRulesService:
    """Service for loading and formatting system rules."""

    def __init__(self, rules_path: str | Path | None = None) -> None:
        self._rules_path = Path(rules_path) if rules_path else self._default_path()
        self._rules: dict[str, Any] = {}
        self._load_rules()

    def _default_path(self) -> Path:
        """Get default rules file path."""
        return Path(__file__).parent.parent.parent.parent / "sample_data" / "system_rules.json"

    def _load_rules(self) -> None:
        """Load rules from JSON file."""
        if self._rules_path.exists():
            with open(self._rules_path) as f:
                self._rules = json.load(f)

    @property
    def rules(self) -> dict[str, Any]:
        """Get raw rules dictionary."""
        return self._rules

    def format_for_prompt(self) -> str:
        """Format system rules for inclusion in SQL generation prompt."""
        if not self._rules:
            return ""

        sections = []

        # Soft delete rule
        if soft_delete := self._rules.get("soft_delete"):
            sections.append(
                f"SOFT DELETE: {soft_delete['description']}. {soft_delete['rule']}"
            )

        # Excluded SELECT columns rule
        if excluded := self._rules.get("excluded_select_columns"):
            cols = ", ".join(excluded.get("columns", []))
            sections.append(
                f"EXCLUDED SELECT COLUMNS: {excluded['description']}.\n"
                f"Columns: {cols}\n"
                f"Rule: {excluded['rule']}"
            )

        # Standard columns
        if std_cols := self._rules.get("standard_columns"):
            col_lines = ["STANDARD COLUMNS:"]
            for col_name, col_info in std_cols.items():
                if isinstance(col_info, dict):
                    desc = col_info.get("description", "")
                    usage = col_info.get("usage", "")
                    rules = col_info.get("rules", [])

                    col_lines.append(f"  - {col_name}: {desc}")
                    if usage:
                        col_lines.append(f"    Usage: {usage}")
                    for rule in rules:
                        col_lines.append(f"    * {rule}")
            sections.append("\n".join(col_lines))

        # SQL conventions
        if conventions := self._rules.get("sql_conventions"):
            conv_lines = ["SQL CONVENTIONS:"]
            for conv in conventions:
                conv_lines.append(f"  - {conv}")
            sections.append("\n".join(conv_lines))

        # Table prefixes
        if prefixes := self._rules.get("table_prefixes"):
            prefix_lines = ["TABLE PREFIXES:"]
            for prefix, desc in prefixes.items():
                prefix_lines.append(f"  - {prefix}*: {desc}")
            sections.append("\n".join(prefix_lines))

        # Key-value search rules
        if kv_search := self._rules.get("key_value_search"):
            kv_lines = [f"KEY_VALUE SEARCH: {kv_search['description']}"]
            kv_lines.append(f"Rule: {kv_search['rule']}")
            if examples := kv_search.get("examples"):
                kv_lines.append("Examples:")
                for example in examples:
                    kv_lines.append(f"  - {example}")
            sections.append("\n".join(kv_lines))

        # Tag aggregation rules
        if tag_agg := self._rules.get("tag_aggregation"):
            tag_lines = [f"TAG AGGREGATION: {tag_agg['description']}"]
            tag_lines.append(f"Rule: {tag_agg['rule']}")
            if patterns := tag_agg.get("patterns"):
                tag_lines.append("Patterns:")
                for name, pattern in patterns.items():
                    tag_lines.append(f"  - {name}: {pattern}")
            if examples := tag_agg.get("examples"):
                tag_lines.append("Examples:")
                for example in examples:
                    tag_lines.append(f"  - {example}")
            sections.append("\n".join(tag_lines))

        return "\n\n".join(sections)


@lru_cache
def get_system_rules_service(rules_path: str | None = None) -> SystemRulesService:
    """Get cached system rules service instance."""
    if rules_path is None:
        from text_to_sql.config import get_settings
        settings = get_settings()
        rules_path = settings.system_rules_path
    return SystemRulesService(rules_path)
