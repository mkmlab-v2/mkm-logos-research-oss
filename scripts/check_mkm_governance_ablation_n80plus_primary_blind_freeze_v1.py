#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Checker — primary blind human 172/172 CSV freeze (per-rater).

Reproduce:
  py scripts/check_mkm_governance_ablation_n80plus_primary_blind_freeze_v1.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_governance_ablation_n80plus_blind_human_v1 import (  # noqa: E402
    ACK_REF,
    BLIND_HUMAN_ROOT,
    RATER_IDS,
    SCORING_DIMENSIONS,
    utc_now,
    write_json,
)

EXPECTED_ROWS = 172
FREEZE_RECEIPT = BLIND_HUMAN_ROOT / "01_PRIMARY_BLIND_FREEZE_RECEIPT.json"
FREEZE_CHECK = (
    ROOT
    / "docs/final/artifacts/mkm_governance_ablation_n80plus_primary_blind_freeze_check_v1_latest.json"
)


def _score_filled(row: dict[str, str]) -> bool:
    for dim in SCORING_DIMENSIONS:
        val = (row.get(dim) or "").strip()
        if val == "":
            return False
        if dim == "appropriate_abstention" and val.upper() not in {"0", "1", "NA"}:
            return False
        elif dim != "appropriate_abstention" and val not in {"0", "1"}:
            return False
    return True


def _load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def main() -> int:
    checks: list[dict[str, Any]] = []
    per_rater: dict[str, Any] = {}
    all_frozen = True

    for rid in RATER_IDS:
        path = BLIND_HUMAN_ROOT / f"{rid}_input_v1.csv"
        if not path.is_file():
            checks.append({"ok": False, "code": f"{rid}_MISSING", "path": str(path)})
            all_frozen = False
            continue
        rows = _load_csv(path)
        filled = sum(1 for r in rows if _score_filled(r))
        ok = len(rows) == EXPECTED_ROWS and filled == EXPECTED_ROWS
        per_rater[rid] = {
            "path": path.as_posix(),
            "row_count": len(rows),
            "filled_count": filled,
            "frozen": ok,
        }
        checks.append(
            {
                "ok": ok,
                "code": f"{rid}_172_OF_172",
                "detail": f"rows={len(rows)} filled={filled}",
            }
        )
        if not ok:
            all_frozen = False

    receipt = {
        "schema": "mkm_governance_ablation_n80plus_primary_blind_freeze_receipt_v1",
        "commander_ack_ref": ACK_REF,
        "generated_at_utc": utc_now(),
        "expected_rows_per_rater": EXPECTED_ROWS,
        "primary_blind_freeze_complete": all_frozen,
        "GOVERNANCE_SUPERIORITY": "NOT_ESTABLISHED",
        "per_rater": per_rater,
        "next_gate": (
            "UNBLIND_ELIGIBLE_ARCHIVE_STAGING"
            if all_frozen
            else "WAIT_FOR_PRIMARY_BLIND_HUMAN_172_OF_172_FREEZE"
        ),
    }
    write_json(FREEZE_RECEIPT, receipt)

    ok = all_frozen
    report = {"ok": ok, "checks": checks, "receipt": str(FREEZE_RECEIPT)}
    FREEZE_CHECK.parent.mkdir(parents=True, exist_ok=True)
    FREEZE_CHECK.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "primary_blind_freeze_complete": all_frozen}, ensure_ascii=False))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
