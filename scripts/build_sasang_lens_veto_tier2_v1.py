#!/usr/bin/env python3
"""Sasang lens Tier2 — force_hold / band-widen-only veto [HYPO][NON_GATING]."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LENS = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/sasang_lens_veto_tier2_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/sasang_lens_veto_tier2_v1_latest.json"

HEAT_THRESHOLD = 0.55
VOL_RAREFACTION_THRESHOLD = 0.45
CONFIDENCE_CEILING = 0.72


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


def _derive_veto(lens: dict[str, Any] | None) -> dict[str, Any]:
    stream = (lens or {}).get("sasang_stream_outputs") if isinstance((lens or {}).get("sasang_stream_outputs"), dict) else {}
    axis = (lens or {}).get("b_track_axis_scores_v1") if isinstance((lens or {}).get("b_track_axis_scores_v1"), dict) else {}
    mr = stream.get("machine_readables") if isinstance(stream.get("machine_readables"), dict) else {}
    heat = float(mr.get("heat_proxy") or axis.get("heat_proxy") or 0.0)
    vol_r = float(mr.get("volatility_rarefaction_proxy") or axis.get("volatility_rarefaction_proxy") or 0.0)
    scores = (lens or {}).get("scores") if isinstance((lens or {}).get("scores"), dict) else {}
    conf = float(scores.get("confidence") or 0.0)
    regime = str(stream.get("regime_hypothesis") or "unknown")
    reasons: list[str] = []
    if heat >= HEAT_THRESHOLD:
        reasons.append("sangyeol_heat_proxy_high")
    if vol_r >= VOL_RAREFACTION_THRESHOLD:
        reasons.append("high_entropy_softmax_proxy")
    if conf <= CONFIDENCE_CEILING and heat >= 0.5:
        reasons.append("bull_hint_low_certainty")
    if regime == "phase_transition":
        reasons.append("phase_transition_regime")
    force_hold = bool(reasons)
    return {
        "force_hold": force_hold,
        "veto_reason_codes": reasons,
        "heat_proxy": heat,
        "volatility_rarefaction_proxy": vol_r,
        "confidence": conf,
        "regime_hypothesis": regime,
        "band_widen_only": force_hold,
        "chase_entry_blocked": force_hold,
        "fusion_weight": 0.0 if force_hold else None,
        "operator_note_ko": (
            "사상 Tier2: force_hold=추격·레버리지 금지(매도 아님). "
            "활성화 시 band widen만 허용·direction flip 금지."
            if force_hold
            else "사상 veto 미발동 — 관측만."
        ),
    }


def build_sasang_tier2(*, lens: dict[str, Any] | None, fusion: dict[str, Any] | None) -> dict[str, Any]:
    veto = _derive_veto(lens)
    sasang_lens = ((fusion or {}).get("lenses") or {}).get("sasang") if isinstance((fusion or {}).get("lenses"), dict) else {}
    return {
        "schema": "sasang_lens_veto_tier2_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "lens_id": "sasang",
        "gating_weight": 0.0,
        "tier2_role": "short_horizon_veto_band_only",
        "horizon_contract": "short_1d",
        "direction_sign": sasang_lens.get("direction_sign") or "bull",
        **veto,
        "forbidden": ["auto_sell_signal", "track_a_merge", "live_order_trigger"],
        "send_gate": "HOLD",
        "pointers": {"sasang_lens": "docs/final/artifacts/sasang_independent_lens_latest.json"},
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_sasang_tier2(lens=_read(args.lens_json), fusion=_read(args.fusion_json))
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")
    print(json.dumps({"ok": True, "force_hold": doc["force_hold"], "reasons": doc["veto_reason_codes"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
