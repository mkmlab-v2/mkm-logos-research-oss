#!/usr/bin/env python3
"""Revert preds jsonl insight fields from calibration30 pre_sweep backup."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
PREDS = ROOT / "reports/myeongri_interpret_lora_v4_preds_locked100_guard448_latest.jsonl"


def main() -> int:
    doc = json.loads(SAMPLE.read_text(encoding="utf-8"))
    pre_by_row = {
        int(s["row_index"]): str(s["mkm_advanced_insight_pre_sweep"])
        for s in doc.get("samples") or []
        if s.get("mkm_advanced_insight_pre_sweep")
    }
    rows = [json.loads(l) for l in PREDS.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    reverted = 0
    for i, row in enumerate(rows):
        ri = i + 1
        if ri not in pre_by_row:
            continue
        raw = str(row.get("prediction_raw", ""))
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        obj["mkm_advanced_insight"] = pre_by_row[ri]
        row["prediction_raw"] = json.dumps(obj, ensure_ascii=False, indent=2)
        row.pop("wording_sweep_applied_at_utc", None)
        reverted += 1
    PREDS.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "reverted_rows": reverted}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
