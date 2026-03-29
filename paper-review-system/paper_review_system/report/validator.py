from __future__ import annotations

from typing import Any


class ReportValidator:
    """Validate protocol invariants before writing final JSON."""

    def validate(self, report: dict[str, Any]) -> None:
        self._assert_array(report, "rule_violations")
        self._assert_array(report.get("logic_analysis", {}).get("core_argument_consistency", {}), "details")
        improvement_plan = report.get("improvement_plan", {})
        self._assert_array(improvement_plan, "semantic_refinement")
        self._assert_array(improvement_plan, "expert_samples")
        self._assert_unique_ids(report.get("rule_violations", []))

    @staticmethod
    def _assert_array(payload: dict[str, Any], key: str) -> None:
        value = payload.get(key)
        if value is None or not isinstance(value, list):
            raise ValueError(f"`{key}` must be a list and cannot be null.")

    @staticmethod
    def _assert_unique_ids(violations: list[dict[str, Any]]) -> None:
        ids = [item["id"] for item in violations if "id" in item]
        if len(ids) != len(set(ids)):
            raise ValueError("`rule_violations.id` contains duplicates.")
