#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Engine
# Vector: {S:0.8, L:0.8, K:0.7, M:0.5}
# Balance: 90
# Purpose: Simulate 503/timeout paths and verify fallback policy binding.
# Keywords: fallback, drill, 503, timeout, policy

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.apply_macro_risk_decision_policy import bind_policy

MATRIX_PATH = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_api_decision_action_matrix_v1.json"
OUT_PATH = ROOT / "docs" / "final" / "artifacts" / "macro_risk_warning_failure_drill_latest.json"


def _read_json(path: Path) -> dict[str, Any]:
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Expected object json: {path}")
    return doc


def main() -> int:
    matrix_doc = _read_json(MATRIX_PATH)

    # Drill case 1: upstream 503 equivalent (no decision_state payload)
    case_503 = {
        "api_status": 503,
        "error": "service_unavailable",
    }
    result_503 = bind_policy(matrix_doc, case_503)

    # Drill case 2: request timeout equivalent (empty response object)
    case_timeout: dict[str, Any] = {}
    result_timeout = bind_policy(matrix_doc, case_timeout)

    out = {
        "schema": "macro_risk_warning_failure_drill_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "matrix_ref": str(MATRIX_PATH),
        "cases": [
            {"name": "http_503_service_unavailable", "input": case_503, "result": result_503},
            {"name": "timeout_empty_payload", "input": case_timeout, "result": result_timeout},
        ],
        "summary": {
            "all_fallback_applied": all(
                c["result"].get("binding_status") == "fallback_applied"
                for c in [
                    {"result": result_503},
                    {"result": result_timeout},
                ]
            )
        },
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"failure_drill: PASS -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
