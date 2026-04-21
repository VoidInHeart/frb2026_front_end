from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
API_JS = ROOT / "src" / "services" / "api.js"


def main() -> int:
    source = API_JS.read_text(encoding="utf-8")

    helper_marker = "async function uploadViaLocalArtifacts({"
    direct_return_marker = "if (hasLocalArtifacts) {\n    return uploadViaLocalArtifacts({"
    parse_marker = 'const data = await requestJsonWithUploadProgress(\n      `${API_BASE_URL}${APP_API_ENDPOINTS.parsePaper.path}`'

    helper_index = source.find(helper_marker)
    direct_return_index = source.find(direct_return_marker)
    parse_index = source.find(parse_marker)
    helper_body = ""
    if helper_index >= 0:
        next_export_index = source.find("export async function uploadPaper({", helper_index)
        helper_body = source[helper_index:next_export_index] if next_export_index >= 0 else source[helper_index:]

    checks = {
        "helper_exists": helper_index >= 0,
        "advanced_import_returns_directly": direct_return_index >= 0,
        "direct_return_happens_before_backend_parse": direct_return_index >= 0
        and parse_index >= 0
        and direct_return_index < parse_index,
        "helper_has_no_self_recursion": "return uploadViaLocalArtifacts({" not in helper_body,
    }

    ok = all(checks.values())
    print(
        json.dumps(
            {
                "ok": ok,
                "checks": checks,
                "positions": {
                    "helper_index": helper_index,
                    "direct_return_index": direct_return_index,
                    "parse_index": parse_index,
                },
                "file": str(API_JS),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
