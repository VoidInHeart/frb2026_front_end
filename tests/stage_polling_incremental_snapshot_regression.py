from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW_FILE = ROOT / "src" / "views" / "ReviewWorkspaceView.vue"


def main() -> int:
    source = VIEW_FILE.read_text(encoding="utf-8")

    checks = {
        "has_displayable_snapshot_helper": "function hasDisplayableStageSnapshot(snapshot)" in source,
        "has_finalized_snapshot_helper": "function hasFinalizedStageSnapshot(snapshot)" in source,
        "has_needs_finalized_snapshot_helper": "function needsFinalizedStageSnapshot(state, stageKey)" in source,
        "completed_stage_rechecks_unfinalized_review": "return !isFinalStageStatus(review.stageStatus);" in source,
        "state_running_fallback_uses_current_stage_only": 'const currentStage = REVIEW_STAGE_ORDER.includes(state?.currentStage)' in source,
        "state_running_fallback_does_not_use_next_stage": ': state?.nextStage;' not in source,
        "current_stage_requires_stage_level_in_progress": 'isInProgressStageStatus(getStateStageStatus(state, currentStage))' in source,
        "missing_snapshot_has_priority_over_running_stage": source.find("const missingSnapshotStage = getCompletedStageMissingSnapshot(state);") < source.find("const runningStage = getRunningStageFromState(state);"),
        "result_reports_displayable": "displayable: hasDisplayableStageSnapshot(snapshot)" in source,
        "result_reports_finalized": "finalized: hasFinalizedStageSnapshot(snapshot)" in source,
        "polling_stops_on_finalized_only": "if (result.finalized) {" in source,
        "displayable_snapshot_keeps_polling": "if (result.displayable) {" in source,
        "ensure_displayed_stage_waits_on_displayable_snapshot": "snapshotResult.displayable ||" in source,
        "legacy_ready_helper_removed": "function hasReadyStageSnapshot(snapshot)" not in source,
        "legacy_ready_short_circuit_removed": "if (result.ready) {" not in source
        and "if (snapshotResult.ready) {" not in source,
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
