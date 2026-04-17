# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.9, L:0.8, K:0.6, M:0.6}
# Balance: 91
# Purpose: Replay saju golden fixtures and emit gate report artifacts.
# Keywords: saju, golden, replay, regression, gate
"""Replay golden saju cases and emit SSOT artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.saju_dual_verify import VerifyInput, verify_dual_saju

DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "saju_golden_cases_v1.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "saju_golden_replay_latest.json"
DEFAULT_LOG = ROOT / "docs" / "final" / "artifacts" / "saju_golden_replay_log.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_replay(fixture_path: Path) -> dict[str, Any]:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    cases = payload.get("cases", [])
    results: list[dict[str, Any]] = []
    failed = 0
    for case in cases:
        case_id = str(case.get("id", "unknown"))
        expected = case.get("expected", {})
        doc = verify_dual_saju(VerifyInput(**case["input"]))
        got_status = str(doc["comparison"]["status"])
        want_status = str(expected.get("status", "REVIEW"))
        reasons = list(doc["comparison"].get("reasons", []))
        mismatch = got_status != want_status
        for reason in expected.get("reasons_contains", []):
            if reason not in reasons:
                mismatch = True
        if mismatch:
            failed += 1
        results.append(
            {
                "id": case_id,
                "expected": expected,
                "actual": {
                    "status": got_status,
                    "reasons": reasons,
                    "pillar_diffs": doc["comparison"].get("pillar_diffs", {}),
                },
                "pass": not mismatch,
            }
        )

    total = len(results)
    passed = total - failed
    return {
        "schema": "saju_golden_replay_report_v1",
        "generated_at_utc": _utc_now(),
        "fixture_path": str(fixture_path),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": (passed / total) if total else 0.0,
            "gate": "PASS" if failed == 0 else "FAIL",
        },
        "results": results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    args = ap.parse_args()

    fixture = args.fixture if args.fixture.is_absolute() else ROOT / args.fixture
    out = args.out if args.out.is_absolute() else ROOT / args.out
    log = args.log if args.log.is_absolute() else ROOT / args.log

    report = run_replay(fixture)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps({"generated_at_utc": report["generated_at_utc"], "summary": report["summary"]}, ensure_ascii=False) + "\n")

    print(str(out))
    print(str(log))
    return 0 if report["summary"]["failed"] == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
