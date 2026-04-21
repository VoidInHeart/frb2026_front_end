from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_FILE = ROOT / "src" / "services" / "api.js"
PANEL_FILE = ROOT / "src" / "components" / "StageFindingsPanel.vue"


def main() -> int:
    api_source = API_FILE.read_text(encoding="utf-8")
    panel_source = PANEL_FILE.read_text(encoding="utf-8")

    checks = {
        "api_has_progress_overview_helper": "function buildFormatProgressOverview(stageOutput, issues = [])" in api_source,
        "api_has_format_issue_extractor": "function extractFormatStageIssues(stageOutput)" in api_source,
        "api_has_displayable_review_helper": "function buildDisplayableStageReview(stageName, payload)" in api_source,
        "stage_snapshot_uses_displayable_review_helper": "review: stageName !== \"summary\" ? buildDisplayableStageReview(stageName, payload) : null" in api_source,
        "running_format_review_uses_extracted_issues": "const issues = extractFormatStageIssues(stageOutput);" in api_source,
        "running_format_review_headline_present": "headline: \"格式审查进行中\"" in api_source,
        "panel_loading_only_blocks_when_no_result": "v-if=\"props.loading && !props.result\"" in panel_source,
        "panel_shows_progress_banner_for_existing_result": "result-banner result-banner-progress" in panel_source,
    }

    ok = all(checks.values())
    print(
        json.dumps(
            {
                "ok": ok,
                "checks": checks,
                "files": [str(API_FILE), str(PANEL_FILE)],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
