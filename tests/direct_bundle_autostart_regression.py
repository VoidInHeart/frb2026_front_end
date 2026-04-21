from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VIEW_FILE = ROOT / "src" / "views" / "LoadingView.vue"


def main() -> int:
    source = VIEW_FILE.read_text(encoding="utf-8")

    checks = {
      "loading_view_imports_trigger_stage_execution": "triggerStageExecution," in source,
      "direct_bundle_auto_start_guard": 'submission.sourceMode === "local-artifacts"' in source,
      "direct_bundle_checks_pending_status": '["", "pending", "created"].includes(initialStageStatus)' in source,
      "direct_bundle_calls_trigger_stage_execution": "await triggerStageExecution({" in source,
      "direct_bundle_refreshes_run_state_after_trigger": "initialRunState = await fetchRunState(runRecord.runId);" in source,
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
