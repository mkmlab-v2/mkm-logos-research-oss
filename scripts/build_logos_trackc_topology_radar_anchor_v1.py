#!/usr/bin/env python3
"""Track C Design handoff anchor — Topology Radar spec from 2030 horizon SSOT (no UI code).

  py scripts/build_logos_trackc_topology_radar_anchor_v1.py
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
HORIZON = ROOT / "docs/final/artifacts/logos_macro_horizon_2030_scenario_v1_latest.json"
GOVERNANCE = ROOT / "docs/final/artifacts/logos_passive_drift_governance_v1_latest.json"
OUT = ROOT / "docs/final/artifacts/logos_trackc_topology_radar_anchor_v1_latest.json"
OUT_MD = ROOT / "docs/final/artifacts/logos_trackc_topology_radar_anchor_v1_latest.md"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _btc_weights(horizon: dict[str, Any] | None) -> dict[str, float]:
    if not horizon:
        return {"base": 0.27, "stress": 0.73}
    by_axis = (horizon.get("scenario_probability_weights") or {}).get("by_axis") or {}
    btc = by_axis.get("btc") or {}
    if btc.get("base") is not None and btc.get("stress") is not None:
        return {"base": float(btc["base"]), "stress": float(btc["stress"])}
    return {"base": 0.27, "stress": 0.73}


def build_anchor() -> dict[str, Any]:
    horizon = _load(HORIZON)
    gov = _load(GOVERNANCE)
    btc = _btc_weights(horizon)
    return {
        "schema": "logos_trackc_topology_radar_anchor_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "[HYPO]",
        "research_rail": "Track_C",
        "policy": {
            "research_only": True,
            "non_gating": True,
            "no_trading_signal": True,
            "no_price_prophecy_headline": True,
            "design_lane_only": True,
        },
        "inputs": {
            "horizon_scenario_json": HORIZON.relative_to(ROOT).as_posix(),
            "passive_drift_governance_json": GOVERNANCE.relative_to(ROOT).as_posix()
            if GOVERNANCE.is_file()
            else None,
            "showroom_json_url": "https://jemaai.cloud/showroom_macro_horizon_2030_slice_v1_latest.json",
        },
        "visual_spec": {
            "module_name": "Track C Topology Radar",
            "departure_from": "GBN 2x2 flat matrix",
            "axes_suggested": [
                {"id": "macro_liquidity", "label_ko": "유동성 레짐", "source": "macro_brief"},
                {"id": "geopolitical_stress", "label_ko": "지정학 스트레스", "source": "forward_weekly"},
                {"id": "narrative_entropy", "label_ko": "내러티브 엔트로피", "source": "logos_chronology"},
                {"id": "civilization_tail", "label_ko": "문명 꼬리 리스크", "source": "general_prophecy"},
            ],
            "btc_scenario_weights": btc,
            "horizon_end_year": (horizon or {}).get("scope", {}).get("horizon_end_year", 2030),
        },
        "design_deliverables": [
            "Radar/spider chart — 4 axes normalized 0–1 (display only)",
            "Stress overlay band — base vs stress weight toggle (default locked to SSOT)",
            "Footer: [HYPO] · not investment advice · no order keys",
        ],
        "implementation_boundary_ko": (
            "본 파일은 Design/Showroom 레인 핸드오프 앵커이다. "
            "파이프라인 Final Action·실매매 Key 주입 금지."
        ),
        "reproduce": "py scripts/build_logos_trackc_topology_radar_anchor_v1.py",
    }


def main() -> int:
    doc = build_anchor()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md = [
        "# Track C Topology Radar — Design anchor",
        "",
        f"**Generated:** `{doc['generated_at_utc']}` · `[HYPO]` · Design lane only",
        "",
        f"BTC base/stress: **{doc['visual_spec']['btc_scenario_weights']}**",
        "",
        "See JSON for axis list and deliverables.",
        "",
        f"Reproduce: `{doc['reproduce']}`",
    ]
    OUT_MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(OUT)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
