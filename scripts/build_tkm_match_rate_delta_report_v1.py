#!/usr/bin/env python3
"""Clinic vs encounter match_rate delta + turn-count breakdown [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_match_rate_delta_report_v1_latest.json"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_clinic_gold() -> list[dict[str, Any]]:
    from scripts.tkm_dummy_row_classifier_v1 import is_dummy_clinic_capture

    rows: list[dict[str, Any]] = []
    base = ROOT / "data/clinic"
    if not base.is_dir():
        return rows
    for path in sorted(base.glob("clinic_constitution_mvp_v1*.jsonl")):
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if not is_dummy_clinic_capture(row):
                rows.append(row)
    return rows


def _load_encounter_gold() -> list[dict[str, Any]]:
    import importlib.util

    from scripts.tkm_dummy_row_classifier_v1 import is_dummy_encounter_sequence

    ledger_path = ROOT / "scripts/encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", ledger_path)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return [r for r in mod.iter_ledger_records(ROOT) if not is_dummy_encounter_sequence(r)]


def _disagreement_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts: Counter[str] = Counter()
    for row in rows:
        agr = row.get("agreement") if isinstance(row.get("agreement"), dict) else {}
        if not agr and isinstance(row.get("physician_closure"), dict):
            agr = row["physician_closure"].get("agreement") or {}
        code = str(agr.get("disagreement_code") or "unknown")
        counts[code] += 1
    return dict(counts)


def build() -> dict[str, Any]:
    from scripts.tkm_clinic_encounter_match_rate_v1 import match_rate

    clinic_rows = _load_clinic_gold()
    enc_rows = _load_encounter_gold()
    clinic_rate = match_rate(clinic_rows)
    enc_rate = match_rate(enc_rows)

    single_turn: list[dict[str, Any]] = []
    multi_turn: list[dict[str, Any]] = []
    for row in enc_rows:
        summary = row.get("sequence_summary") if isinstance(row.get("sequence_summary"), dict) else {}
        tc = int(summary.get("turn_count") or len(row.get("turns") or []) or 1)
        if tc >= 3:
            multi_turn.append(row)
        else:
            single_turn.append(row)

    single_rate = match_rate(single_turn)
    multi_rate = match_rate(multi_turn)
    delta = (
        round(float(enc_rate) - float(clinic_rate), 4)
        if clinic_rate is not None and enc_rate is not None
        else None
    )

    return {
        "schema": "tkm_match_rate_delta_report_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "send_gate": "HOLD",
        "physician_gold_only": True,
        "clinic_match_rate": clinic_rate,
        "encounter_match_rate": enc_rate,
        "match_rate_delta_encounter_minus_clinic": delta,
        "encounter_breakdown": {
            "single_turn_count": len(single_turn),
            "multiturn_count": len(multi_turn),
            "single_turn_match_rate": single_rate,
            "multiturn_match_rate": multi_rate,
        },
        "clinic_disagreement_codes": _disagreement_counts(clinic_rows),
        "encounter_disagreement_codes": _disagreement_counts(enc_rows),
        "delta_kpi_ok": delta is not None,
        "note_ko": "음수 delta = encounter lane 불일치 비율이 clinic보다 높음(멀티턴·변환 경로 영향 가능).",
        "reproduce": "py scripts/build_tkm_match_rate_delta_report_v1.py",
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
                "ok": doc.get("delta_kpi_ok"),
                "delta": doc.get("match_rate_delta_encounter_minus_clinic"),
            }
        )
    )
    return 0 if doc.get("delta_kpi_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
