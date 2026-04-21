from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW_FILE = ROOT / "src" / "views" / "ReviewWorkspaceView.vue"


def main() -> int:
    source = VIEW_FILE.read_text(encoding="utf-8")
    decision_block_start = source.find("const decisionActions = computed(() => {")
    footer_block_start = source.find("const footerAction = computed(() => {")
    footer_block_end = source.find("function refreshSummarySnapshot()", footer_block_start)
    decision_block = source[decision_block_start:footer_block_start] if decision_block_start >= 0 and footer_block_start >= 0 else ""
    footer_block = source[footer_block_start:footer_block_end] if footer_block_start >= 0 and footer_block_end >= 0 else ""

    checks = {
        "decision_actions_follow_visible_stage": 'visibleStage.value === "summary"' in decision_block,
        "decision_actions_no_displayed_summary_guard": 'currentStageDisplayed.value === "summary"' not in decision_block,
        "footer_action_follows_visible_stage": 'visibleStage.value === "summary"' in footer_block,
        "footer_action_reads_allowed_actions": "const allowedActions = Array.isArray(runState.value?.allowedActions)" in footer_block,
        "footer_action_requires_continue_capability": "const canContinue = allowedActions.length === 0 || allowedActions.includes(\"continue\")" in footer_block,
        "footer_action_no_displayed_summary_guard": 'currentStageDisplayed.value === "summary"' not in footer_block,
    }

    ok = all(checks.values())
    print(
        json.dumps(
            {
                "ok": ok,
                "checks": checks,
                "file": str(VIEW_FILE),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
