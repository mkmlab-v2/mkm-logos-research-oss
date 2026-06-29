#!/usr/bin/env python3
"""Validate all rows in Han Vocology KM-VHI pilot JSONL (B-track · M8)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
QUESTIONNAIRE = ROOT / "docs/final/artifacts/km_vhi_questionnaire_v0_1_latest.json"
DEFAULT_JSONL = ROOT / "reports/han_vocology_km_vhi_pilot_records.jsonl"
OUT = ROOT / "reports/han_vocology_km_vhi_pilot_jsonl_validation_v1_latest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.validate_han_vocology_km_vhi_pilot_record_v1 import validate_record  # noqa: E402


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def validate_jsonl(path: Path, *, questionnaire: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    line_results: list[dict[str, Any]] = []
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        record = json.loads(stripped)
        result = validate_record(record, questionnaire=questionnaire)
        result["line"] = i
        result["pseudonym_id"] = record.get("pseudonym_id")
        line_results.append(result)
        rows.append(record)

    dup_keys = [
        (r.get("pseudonym_id"), r.get("visit_week"))
        for r in rows
    ]
    unique = len(dup_keys) == len(set(dup_keys))

    summary_by_patient: dict[str, list[int]] = {}
    for r in rows:
        pid = str(r.get("pseudonym_id") or "")
        week_raw = r.get("visit_week")
        summary_by_patient.setdefault(pid, []).append(
            int(week_raw) if week_raw is not None else -1
        )

    ok = all(r["ok"] for r in line_results) and unique and bool(line_results)
    return {
        "ok": ok,
        "row_count": len(line_results),
        "unique_pseudonym_visit": unique,
        "patients": summary_by_patient,
        "rows": line_results,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--questionnaire", type=Path, default=QUESTIONNAIRE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.jsonl.is_file():
        print(json.dumps({"ok": False, "error": "jsonl_missing", "path": str(args.jsonl)}, ensure_ascii=False))
        return 1

    questionnaire = json.loads(args.questionnaire.read_text(encoding="utf-8"))
    result = validate_jsonl(args.jsonl, questionnaire=questionnaire)
    result["generated_at_utc"] = _utc()
    result["jsonl"] = str(args.jsonl)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "row_count": result["row_count"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
