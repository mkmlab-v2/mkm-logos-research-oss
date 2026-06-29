#!/usr/bin/env python3
"""Build TKM encounter_sequence cross-lens KPI (L4/L5/L6) [HYPO]."""

from __future__ import annotations

import argparse
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/tkm_encounter_sequence_cross_lens_kpi_v1_latest.json"
DUAL = ROOT / "reports/tkm_clinic_encounter_dual_lane_summary_v1_latest.json"
MYEONGNI = ROOT / "reports/tkm_encounter_sequence_myeongni_kpi_v1_latest.json"
LOGOS = ROOT / "reports/tkm_encounter_sequence_logos_kpi_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iter_latest_records() -> list[dict[str, Any]]:
    path = ROOT / "scripts/encounter_sequence_ledger_v1.py"
    spec = importlib.util.spec_from_file_location("encounter_sequence_ledger_v1", path)
    if spec is None or spec.loader is None:
        return []
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    sidecar_path = ROOT / "scripts/tkm_encounter_sequence_logos_sidecar_v1.py"
    sidecar_spec = importlib.util.spec_from_file_location("tkm_encounter_sequence_logos_sidecar_v1", sidecar_path)
    if sidecar_spec is None or sidecar_spec.loader is None:
        return []
    sidecar_mod = importlib.util.module_from_spec(sidecar_spec)
    sidecar_spec.loader.exec_module(sidecar_mod)
    return list(sidecar_mod.latest_records_by_sequence_id(mod.iter_ledger_records(ROOT)))


def build() -> dict[str, Any]:
    dual = _load(DUAL)
    myeongni = _load(MYEONGNI)
    logos = _load(LOGOS)
    records = _iter_latest_records()

    dual_gold = dual.get("physician_gold_only") if isinstance(dual.get("physician_gold_only"), dict) else {}
    m_gold = myeongni.get("physician_gold_only") if isinstance(myeongni.get("physician_gold_only"), dict) else {}
    l_gold = logos.get("physician_gold_only") if isinstance(logos.get("physician_gold_only"), dict) else {}

    l4_enc_rate = float(dual_gold.get("encounter_match_rate") or 0.0)
    l5_eng_rate = float(m_gold.get("engine_report_linked_rate") or 0.0)
    l6_anchor_rate = float(l_gold.get("logos_anchor_linked_rate") or 0.0)
    resonance_index = round((l4_enc_rate + l5_eng_rate + l6_anchor_rate) / 3.0, 4)

    motif_counts: dict[str, int] = {}
    all_logos = logos.get("all_ledger") if isinstance(logos.get("all_ledger"), dict) else {}
    raw_motifs = all_logos.get("motif_file_stem_counts")
    if isinstance(raw_motifs, dict):
        motif_counts = {str(k): int(v) for k, v in raw_motifs.items()}
    motif_total = sum(motif_counts.values())
    motif_top1_count = max(motif_counts.values()) if motif_counts else 0
    motif_top1_share = round(motif_top1_count / motif_total, 4) if motif_total else None
    motif_skew_gate_ok = motif_top1_share is not None and motif_top1_share < 0.65

    complete_rows = 0
    for row in records:
        l5 = row.get("l5_myeongni_ref")
        l6 = row.get("l6_logos_ref")
        if isinstance(l5, dict) and isinstance(l6, dict):
            complete_rows += 1

    kpi_ok = (
        dual.get("dual_lane_ok") is True
        and myeongni.get("physician_gold_engine_ok") is True
        and logos.get("physician_gold_logos_ok") is True
        and complete_rows >= 1
        and motif_skew_gate_ok
    )

    return {
        "schema": "tkm_encounter_sequence_cross_lens_kpi_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "domain_lane": "tkm_korean_han_medicine",
        "send_gate": "HOLD",
        "non_gating": True,
        "kpi_ok": kpi_ok,
        "l4_l5_l6_complete_row_count": complete_rows,
        "l4_sasang_encounter_match_rate": l4_enc_rate,
        "l5_myeongni_engine_linked_rate": l5_eng_rate,
        "l6_logos_anchor_linked_rate": l6_anchor_rate,
        "cross_lens_resonance_index": resonance_index,
        "motif_top1_share": motif_top1_share,
        "motif_top1_count": motif_top1_count,
        "motif_skew_gate_ok": motif_skew_gate_ok,
        "motif_file_stem_counts": motif_counts,
        "note_ko": "Cross-lens KPI [HYPO][NON_GATING] — L4/L5/L6 관측 공진 지표, Track A 합선 금지.",
        "reproduce": "py scripts/build_tkm_encounter_sequence_cross_lens_kpi_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("kpi_ok"), "resonance": doc.get("cross_lens_resonance_index")}))
    return 0 if doc.get("kpi_ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
