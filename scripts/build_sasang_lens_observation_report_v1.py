#!/usr/bin/env python3
"""Sasang observation report: independent lens vs market overlay (not hit-rate claim)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "reports" / "sasang_lens_observation_report_v1_latest.json"
OUT_MD = ROOT / "reports" / "sasang_lens_observation_report_v1_latest.md"


def _read(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def build_sasang_lens_observation_report(workspace: Path | None = None) -> Dict[str, Any]:
    ws = (workspace or ROOT).resolve()
    art = ws / "docs" / "final" / "artifacts"
    sa = _read(art / "sasang_independent_lens_latest.json")
    market = _read(art / "market_sasang_lens_latest.json")
    hr = _read(art / "sasang_high_reliability_gate_latest.json")
    fusion = _read(art / "sasang_4agent_fusion_gate_latest.json")
    per_lens = _read(art / "prophecy_hit_rate_per_lens_latest.json")

    sa_scores = sa.get("scores") if isinstance(sa.get("scores"), dict) else {}
    market_scores = market.get("scores") if isinstance(market.get("scores"), dict) else {}
    sa_out = sa.get("sasang_stream_outputs") if isinstance(sa.get("sasang_stream_outputs"), dict) else {}
    mr = sa_out.get("machine_readables") if isinstance(sa_out.get("machine_readables"), dict) else {}

    shadow_hit = None
    n_eval = None
    legs = per_lens.get("legs") if isinstance(per_lens.get("legs"), dict) else {}
    for inst_legs in legs.values():
        if not isinstance(inst_legs, dict):
            continue
        for row in inst_legs.get("lenses") or []:
            if isinstance(row, dict) and row.get("lens_id") == "sasang":
                shadow_hit = row.get("price_directional_hit_rate")
                n_eval = row.get("n_evaluated")
                break

    warnings: List[str] = []
    if not sa:
        warnings.append("missing sasang_independent_lens_latest.json")
    if not market:
        warnings.append("missing market_sasang_lens_latest.json")

    return {
        "schema": "sasang_lens_observation_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "not_hit_rate_proof": True,
        "separation": {
            "independent_lens": "sasang_independent_lens_latest.json",
            "market_overlay_lens": "market_sasang_lens_latest.json",
            "auto_merge_forbidden": True,
            "clinical_bridge_forbidden": True,
        },
        "snapshots": {
            "direction_score": sa_scores.get("direction_score"),
            "confidence": sa_scores.get("confidence"),
            "heat_proxy": mr.get("heat_proxy"),
            "market_direction_score": market_scores.get("direction_score"),
            "market_force_hold": (market.get("veto") or {}).get("force_hold"),
        },
        "gates": {
            "high_reliability_decision": hr.get("decision"),
            "fusion_decision": fusion.get("decision"),
            "recall_macro": (hr.get("snapshot") or {}).get("recall_macro"),
            "brier_score": (hr.get("snapshot") or {}).get("brier_score"),
        },
        "shadow_price_hit": {
            "source": "prophecy_hit_rate_per_lens_latest.json",
            "lens_id": "sasang",
            "price_directional_hit_rate": shadow_hit,
            "n_evaluated": n_eval,
            "counterfactual_snapshot": True,
            "note_ko": per_lens.get("zeroing_note") or "B-track shadow only",
        },
        "warnings": warnings,
        "separation_contract_ok": market.get("schema") == "market_sasang_lens_v1" and bool(sa),
    }


def write_report(workspace: Path | None = None) -> tuple[Path, Path]:
    ws = (workspace or ROOT).resolve()
    doc = build_sasang_lens_observation_report(ws)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    sh = doc.get("shadow_price_hit") if isinstance(doc.get("shadow_price_hit"), dict) else {}
    lines = [
        "# 사상 관측 리포트 v1",
        "",
        f"- generated: {doc['generated_at_utc']}",
        "- `[HYPO]` · `research_only`",
        "",
        f"- separation_ok: {doc.get('separation_contract_ok')}",
        f"- heat_proxy: {doc['snapshots'].get('heat_proxy')}",
        f"- fusion: {doc['gates'].get('fusion_decision')}",
        f"- shadow hit (counterfactual): {sh.get('price_directional_hit_rate')} n={sh.get('n_evaluated')}",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return OUT_JSON, OUT_MD


def main() -> int:
    j, m = write_report()
    print(f"WROTE: {j}")
    print(f"WROTE: {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
