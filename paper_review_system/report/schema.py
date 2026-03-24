from __future__ import annotations


REVIEW_REPORT_SCHEMA = {
    "type": "object",
    "required": ["project_metadata", "logic_analysis", "rule_violations", "improvement_plan"],
    "properties": {
        "project_metadata": {"type": "object"},
        "logic_analysis": {"type": "object"},
        "rule_violations": {"type": "array"},
        "improvement_plan": {"type": "object"},
    },
}
