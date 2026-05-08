#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description="Append AGCT stage2 compare latest snapshot to history log.")
    root = Path(__file__).resolve().parents[1]
    ap.add_argument(
        "--compare-json",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_candidate_compare_v1_latest.json",
    )
    ap.add_argument(
        "--history-jsonl",
        type=Path,
        default=root / "reports" / "agct_sasang_stage2_compare_history_v1.jsonl",
    )
    ns = ap.parse_args()

    compare = _read_json(ns.compare_json)
    row = {
        "schema": "agct_sasang_stage2_compare_history_row_v1",
        "appended_at_utc": _utc_now(),
        "source_generated_at_utc": compare.get("generated_at_utc"),
        "decision_label": compare.get("decision", {}).get("label"),
        "decision_reasons": compare.get("decision", {}).get("reasons", []),
        "baseline_status": compare.get("baseline", {}).get("status"),
        "baseline_repro_trials": compare.get("baseline", {}).get("repro_trials"),
        "candidate_status": compare.get("candidate", {}).get("status"),
        "candidate_decision_label": compare.get("candidate", {}).get("decision_label"),
        "candidate_checks_pass_all": compare.get("candidate", {}).get("checks_pass_all"),
    }

    ns.history_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with ns.history_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"APPENDED: {ns.history_jsonl.resolve()} decision={row['decision_label']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
