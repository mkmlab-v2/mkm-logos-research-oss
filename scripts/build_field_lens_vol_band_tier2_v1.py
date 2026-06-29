#!/usr/bin/env python3
"""Field lens Tier2 — vol-linked band policy snapshot [HYPO][B-track]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_BAND_WF = ROOT / "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json"
DEFAULT_FIELD_GRAPH = ROOT / "reports/field_kospi_event_graph_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/field_lens_vol_band_tier2_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def build_field_tier2(*, band_wf: dict[str, Any] | None, field_graph: dict[str, Any] | None) -> dict[str, Any]:
    band_wf = band_wf or {}
    pol = band_wf.get("band_policy") if isinstance(band_wf.get("band_policy"), dict) else {}
    hold = band_wf.get("holdout_pooled") if isinstance(band_wf.get("holdout_pooled"), dict) else {}
    cmp_ = band_wf.get("comparison") if isinstance(band_wf.get("comparison"), dict) else {}
    active = hold.get("band_active") if isinstance(hold.get("band_active"), dict) else {}
    vol_arm = hold.get("band_conflict_vol_widen") if isinstance(hold.get("band_conflict_vol_widen"), dict) else {}
    return {
        "schema": "field_lens_vol_band_tier2_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "lens_id": "field",
        "gating_eligible": True,
        "tier2_role": "vol_band_coverage_gate",
        "policy": {
            "direction_unchanged": bool(pol.get("direction_unchanged", True)),
            "vol_band_k": pol.get("vol_band_k"),
            "vol_window": pol.get("vol_window"),
            "shock_scale": pol.get("shock_scale"),
            "conflict_shock_scale": pol.get("conflict_shock_scale"),
            "preferred_arm": "band_conflict_vol_widen",
        },
        "holdout_metrics": {
            "band_active_rate": active.get("band_hit_rate"),
            "band_conflict_vol_widen_rate": vol_arm.get("band_hit_rate"),
            "delta_vol_widen_minus_active": cmp_.get("delta_conflict_vol_widen_minus_active_band_holdout"),
            "direction_soft_hit_rate": vol_arm.get("direction_soft_hit_rate"),
        },
        "promotion_candidate": band_wf.get("promotion_candidate"),
        "operator_note_ko": (
            "Field Tier2: shock+conflict 시 방향 유지·vol 연동 band 확대만 적용. "
            "direction head 자동 승격 금지."
        ),
        "send_gate": "HOLD",
        "pointers": {
            "band_coverage_wf": "reports/kospi_four_lens_conflict_band_coverage_wf_v1_latest.json",
            "field_event_graph": "reports/field_kospi_event_graph_v1_latest.json",
            "field_graph_nodes": (field_graph or {}).get("node_count"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--band-wf-json", type=Path, default=DEFAULT_BAND_WF)
    ap.add_argument("--field-graph-json", type=Path, default=DEFAULT_FIELD_GRAPH)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_field_tier2(band_wf=_read(args.band_wf_json), field_graph=_read(args.field_graph_json))
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json), "delta": doc["holdout_metrics"]["delta_vol_widen_minus_active"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
