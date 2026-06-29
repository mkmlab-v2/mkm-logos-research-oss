#!/usr/bin/env python3
"""Build Han Vocology OSCE rubric SSOT JSON (B-track · M20)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/han_vocology_osce_rubric_v1_latest.json"
REPORT = ROOT / "reports/han_vocology_osce_rubric_build_v1_latest.json"

STATIONS: list[dict[str, Any]] = [
    {"id": "ST-01", "cb_id": "CB-06-A", "task_ko": "SOAP 15m", "policy": "B1", "points": 25},
    {"id": "ST-02", "cb_id": "CB-08-A", "task_ko": "A1 금지문", "policy": "A1", "points": 25},
    {"id": "ST-03", "cb_id": "CB-10-A", "task_ko": "L1 PPI", "policy": "L1", "points": 25},
    {"id": "ST-04", "cb_id": "CB-09-A", "task_ko": "C1 BoNT", "policy": "C1", "points": 25},
    {"id": "ST-05", "cb_id": "CB-11", "task_ko": "MPT", "policy": "B1", "points": 25},
    {"id": "ST-06", "cb_id": "CB-12", "task_ko": "GRBAS", "policy": "B1", "points": 25},
    {"id": "ST-07", "cb_id": "CB-13", "task_ko": "RSI", "policy": "L1", "points": 25},
    {"id": "ST-08", "cb_id": "CB-16", "task_ko": "SD 감별", "policy": "C1", "points": 25},
]

DIMENSIONS: list[dict[str, Any]] = [
    {"id": "policy", "label_ko": "정책 VT/BoNT/PPI", "max_points": 25},
    {"id": "soap", "label_ko": "SOAP 구조", "max_points": 25},
    {"id": "km_vhi", "label_ko": "KM-VHI 해석", "max_points": 20},
    {"id": "forbidden_phrase", "label_ko": "금지문 회피", "max_points": 20},
    {"id": "fact_hypo_tag", "label_ko": "FACT/HYPO 태그", "max_points": 10},
]

PRACTICE_RUBRIC: list[dict[str, Any]] = [
    {"id": "red_flag", "label_ko": "Red flag", "max_points": 15},
    {"id": "policy", "label_ko": "정책 B1/A1/L1/C1", "max_points": 20},
    {"id": "soap", "label_ko": "SOAP", "max_points": 20},
    {"id": "km_vhi", "label_ko": "KM-VHI 해석", "max_points": 15},
    {"id": "vt_referral", "label_ko": "VT 의뢰", "max_points": 10},
    {"id": "patient_edu", "label_ko": "환자교육", "max_points": 10},
    {"id": "forbidden_zero", "label_ko": "금지멘트 0", "max_points": 10},
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build() -> dict[str, Any]:
    total_station = sum(s["points"] for s in STATIONS)
    return {
        "schema": "han_vocology_osce_rubric_v1",
        "version": "0.1.0",
        "track": "B",
        "send_gate": "HOLD",
        "patient_facing": "blocked",
        "updated_at_utc": _utc(),
        "source_case_bank": "docs/research/HAN_VOCOLOGY_CASE_BANK_V0_1.md",
        "source_sections": ["§10", "§37", "§55", "§57"],
        "pass_rules": {
            "station_pool_min_points": 160,
            "station_pool_max_points": total_station,
            "station_pool_pass_pct": 80,
            "facilitator_rubric_min_pct": 70,
            "practice_rubric_min_points": 80,
            "graduation_rubric_min_points": 70,
            "red_flag_required_correct": 1,
        },
        "stations": STATIONS,
        "station_dimensions": DIMENSIONS,
        "practice_rubric_100": PRACTICE_RUBRIC,
        "graduation_rubric_100": [
            {"id": "volume_gap_350", "label_ko": "gap builder ≥350", "max_points": 20},
            {"id": "osce_55", "label_ko": "OSCE §55", "max_points": 30},
            {"id": "cb_coverage", "label_ko": "CB-06~16", "max_points": 25},
            {"id": "policy_spot", "label_ko": "정책 spot", "max_points": 15},
            {"id": "ethics_hold", "label_ko": "윤리·HOLD", "max_points": 10},
        ],
        "cb_ids_covered": sorted({s["cb_id"] for s in STATIONS}),
        "disclaimer_ko": "교육·[HYPO] OSCE 루브릭 — 임상 면허·IRB·send_gate 해제와 무관.",
        "reproduce": [
            "py scripts/build_han_vocology_osce_rubric_v1.py",
            "py scripts/validate_han_vocology_osce_rubric_v1.py",
        ],
    }


def main() -> int:
    doc = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        json.dumps(
            {
                "schema": "han_vocology_osce_rubric_build_v1",
                "ok": True,
                "generated_at_utc": _utc(),
                "out": str(OUT),
                "station_count": len(doc["stations"]),
                "total_points": doc["pass_rules"]["station_pool_max_points"],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "stations": len(doc["stations"]),
                "out": str(OUT),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
