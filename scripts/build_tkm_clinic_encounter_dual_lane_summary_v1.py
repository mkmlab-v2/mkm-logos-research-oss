#!/usr/bin/env python3
"""Dual-lane KPI: physician_gold_only vs operational_dummy [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"

import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_clinic_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    base = ROOT / "data/clinic"
    if not base.is_dir():
        return rows
    for path in sorted(base.glob("clinic_constitution_mvp_v1*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _load_encounter_rows() -> list[dict[str, Any]]:
    import importlib.util

    ledger_path = ROOT / "scripts/encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.iter_ledger_records(ROOT)


def _match_rate(rows: list[dict[str, Any]]) -> float | None:
    from scripts.tkm_clinic_encounter_match_rate_v1 import match_rate

    return match_rate(rows)


def build() -> dict[str, Any]:
    from scripts.tkm_dummy_row_classifier_v1 import is_dummy_clinic_capture, is_dummy_encounter_sequence

    clinic_rows = _load_clinic_rows()
    enc_rows = _load_encounter_rows()
    clinic_gold = [r for r in clinic_rows if not is_dummy_clinic_capture(r)]
    clinic_dummy = [r for r in clinic_rows if is_dummy_clinic_capture(r)]
    enc_gold = [r for r in enc_rows if not is_dummy_encounter_sequence(r)]
    enc_dummy = [r for r in enc_rows if is_dummy_encounter_sequence(r)]

    dual_ok = len(clinic_gold) >= 1 and len(enc_gold) >= 1
    return {
        "schema": "tkm_clinic_encounter_dual_lane_summary_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "dual_lane_ok": dual_ok,
        "physician_gold_only": {
            "clinic_capture_count": len(clinic_gold),
            "encounter_sequence_count": len(enc_gold),
            "clinic_match_rate": _match_rate(clinic_gold),
            "encounter_match_rate": _match_rate(enc_gold),
        },
        "operational_dummy": {
            "clinic_capture_count": len(clinic_dummy),
            "encounter_sequence_count": len(enc_dummy),
            "label": "operational (post-processor / bootstrap dummy only)",
        },
        "delta": {
            "clinic_dummy_minus_gold_count": len(clinic_dummy),
            "encounter_dummy_minus_gold_count": len(enc_dummy),
        },
        "note_ko": "헤드라인 KPI는 physician_gold_only만. dummy는 운영·부트스트랩 증거.",
        "reproduce": "py scripts/build_tkm_clinic_encounter_dual_lane_summary_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["dual_lane_ok"],
                "clinic_gold": doc["physician_gold_only"]["clinic_capture_count"],
                "encounter_match_rate": doc["physician_gold_only"].get("encounter_match_rate"),
            }
        )
    )
    return 0 if doc["dual_lane_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
