#!/usr/bin/env python3
"""Offline bench for BigSet Tier-0 atypical signal detector — labeled fixture cases.

Compares ``detect()`` output against ``tests/fixtures/bigset/atypical_bench_cases_v1.json``.
Observability only; exit 0 when all cases pass.

Reproducible:
  py scripts/bench_bigset_tier0_atypical_signal_v1.py
"""

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

from scripts.detect_bigset_tier0_atypical_signal_v1 import detect

DEFAULT_CASES = ROOT / "tests/fixtures/bigset/atypical_bench_cases_v1.json"
DEFAULT_OUT = ROOT / "reports/bigset_tier0_atypical_bench_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    case_id = str(case.get("case_id") or "unknown")
    rows = case.get("rows") or []
    expect = case.get("expect") or {}
    doc = detect(rows)
    signals = doc.get("signals") or []
    types_found = sorted({str(s.get("signal_type") or "") for s in signals if isinstance(s, dict)})

    min_count = int(expect.get("min_signal_count", 0))
    max_count = expect.get("max_signal_count")
    expected_types = sorted(str(t) for t in (expect.get("signal_types") or []))

    ok_count = len(signals) >= min_count
    if max_count is not None:
        ok_count = ok_count and len(signals) <= int(max_count)

    ok_types = types_found == expected_types
    ok = ok_count and ok_types

    return {
        "case_id": case_id,
        "ok": ok,
        "signal_count": len(signals),
        "types_found": types_found,
        "expected_types": expected_types,
        "min_signal_count": min_count,
        "max_signal_count": max_count,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.cases.is_file():
        print(json.dumps({"ok": False, "error": f"missing cases: {args.cases}"}), file=sys.stderr)
        return 2

    cases = json.loads(args.cases.read_text(encoding="utf-8"))
    if not isinstance(cases, list):
        print(json.dumps({"ok": False, "error": "cases must be a JSON array"}), file=sys.stderr)
        return 2

    results = [evaluate_case(c) for c in cases if isinstance(c, dict)]
    pass_count = sum(1 for r in results if r.get("ok"))
    report = {
        "schema": "bigset_tier0_atypical_bench_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "cases_total": len(results),
        "cases_pass": pass_count,
        "cases_fail": len(results) - pass_count,
        "quality_ok": pass_count == len(results) and len(results) > 0,
        "results": results,
        "reproduce": "py scripts/bench_bigset_tier0_atypical_signal_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["quality_ok"],
                "cases_pass": pass_count,
                "cases_total": len(results),
                "report": str(args.out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["quality_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
