#!/usr/bin/env python3
"""Dummy vs non-dummy benchmark rebalance report [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "reports/sasang_joint_benchmark_composition_v1_latest.json"
OUT = ROOT / "reports/sasang_joint_benchmark_dummy_rebalance_v1_latest.json"

MIN_NON_DUMMY = 5
MIN_NON_DUMMY_SHARE = 0.45


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    comp = _load(COMP)
    total = int(comp.get("rows_total") or 0)
    dummy = int(comp.get("rows_dummy") or 0)
    non_dummy = int(comp.get("rows_non_dummy") or 0)
    share = (non_dummy / total) if total else 0.0
    rebalance_ok = non_dummy >= MIN_NON_DUMMY or share >= MIN_NON_DUMMY_SHARE
    return {
        "schema": "sasang_joint_benchmark_dummy_rebalance_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "rows_total": total,
        "rows_dummy": dummy,
        "rows_non_dummy": non_dummy,
        "non_dummy_share": round(share, 4),
        "thresholds": {
            "min_non_dummy": MIN_NON_DUMMY,
            "min_non_dummy_share": MIN_NON_DUMMY_SHARE,
        },
        "rebalance_ok": rebalance_ok,
        "rebalance_status": "balanced_enough" if rebalance_ok else "dummy_heavy",
        "composition_ref": str(COMP).replace("\\", "/"),
        "reproduce": "py scripts/build_sasang_joint_benchmark_dummy_rebalance_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["rebalance_ok"], "non_dummy_share": doc["non_dummy_share"]}))
    return 0 if doc["rebalance_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
