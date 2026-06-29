#!/usr/bin/env python3
"""Unified disagreement KPI: clinic MVP + encounter_sequence [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CLINIC_SUMMARY = ROOT / "reports/clinic_mvp_disagreement_summary_latest.json"
ENCOUNTER_SUMMARY = ROOT / "reports/encounter_sequence_summary_v1_latest.json"
OUT = ROOT / "reports/tkm_clinic_encounter_unified_disagreement_summary_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build() -> dict[str, Any]:
    clinic = _load(CLINIC_SUMMARY)
    enc = _load(ENCOUNTER_SUMMARY)
    clinic_rows = int(clinic.get("n_lines_valid") or clinic.get("row_count") or 0)
    enc_rows = int(enc.get("sequence_count") or 0)
    clinic_rate = clinic.get("match_rate")
    enc_rate = enc.get("physician_agreement_rate")
    unified_ok = clinic_rows >= 1 and enc_rows >= 1
    return {
        "schema": "tkm_clinic_encounter_unified_disagreement_summary_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "unified_ok": unified_ok,
        "clinic_mvp": {
            "row_count": clinic_rows,
            "physician_agreement_rate": clinic_rate,
            "disagreement_code_histogram": clinic.get("disagreement_code_counts"),
            "summary_path": str(CLINIC_SUMMARY).replace("\\", "/"),
        },
        "encounter_sequence": {
            "sequence_count": enc_rows,
            "physician_agreement_rate": enc_rate,
            "disagreement_count": enc.get("disagreement_count"),
            "summary_path": str(ENCOUNTER_SUMMARY).replace("\\", "/"),
        },
        "note_ko": "clinic MVP gold + encounter_sequence ledger 이중 보고; Track A·auto-training 금지",
        "reproduce": "py scripts/build_tkm_clinic_encounter_unified_disagreement_summary_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["unified_ok"], "clinic_rows": doc["clinic_mvp"]["row_count"]}))
    return 0 if doc["unified_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
