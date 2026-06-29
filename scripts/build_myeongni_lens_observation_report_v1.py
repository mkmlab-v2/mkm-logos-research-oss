#!/usr/bin/env python3
"""Myeongni observation report: birth-chain vs market overlay separation (not hit-rate claim)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[1]
OUT_JSON = ROOT / "reports" / "myeongni_lens_observation_report_v1_latest.json"
OUT_MD = ROOT / "reports" / "myeongni_lens_observation_report_v1_latest.md"


def _read(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _collect_lens_hits(
    per_lens: Dict[str, Any],
    lens_ids: tuple[str, ...],
) -> tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, Dict[str, Any]]], List[str]]:
    """Counterfactual shadow hits from per-lens bench ([HYPO] · not headline)."""
    primary: Dict[str, Dict[str, Any]] = {}
    by_instrument: Dict[str, Dict[str, Dict[str, Any]]] = {lid: {} for lid in lens_ids}
    legs = per_lens.get("legs") if isinstance(per_lens.get("legs"), dict) else {}
    instruments_seen: List[str] = []
    for instrument, block in legs.items():
        if not isinstance(block, dict):
            continue
        inst = str(instrument)
        instruments_seen.append(inst)
        for row in block.get("lenses") or []:
            if not isinstance(row, dict):
                continue
            lid = str(row.get("lens_id") or "")
            if lid not in lens_ids:
                continue
            snap = {
                "instrument": inst,
                "price_directional_hit_rate": row.get("price_directional_hit_rate"),
                "n_evaluated": row.get("n_evaluated"),
                "price_hits": row.get("price_hits"),
                "predicted_direction": row.get("predicted_direction"),
                "confidence_band": row.get("confidence_band"),
            }
            by_instrument.setdefault(lid, {})[inst] = snap
            if lid not in primary or primary[lid].get("instrument") == "btc":
                primary[lid] = snap
    return primary, by_instrument, sorted(set(instruments_seen))


def _ko_dir(score: Any) -> str:
    try:
        x = float(score)
        if x > 0.08:
            return "상승(중기)"
        if x < -0.08:
            return "하락(중기)"
        return "횡보(중기)"
    except (TypeError, ValueError):
        return "—"


def build_myeongni_lens_observation_report(workspace: Path | None = None) -> Dict[str, Any]:
    ws = (workspace or ROOT).resolve()
    art = ws / "docs" / "final" / "artifacts"
    chain = _read(art / "myeongni_independent_lens_from_chain_latest.json")
    lens = _read(art / "myeongni_independent_lens_latest.json")
    market = _read(art / "market_myeongni_lens_latest.json")
    gate = _read(art / "independent_lens_shadow_gate_latest.json")
    stage2 = _read(art / "myeongni_stage2_realset_gate_latest.json")
    promo = _read(art / "myeongni_promotion_gate_latest.json")
    per_lens = _read(art / "prophecy_hit_rate_per_lens_latest.json")
    shadow_hits, shadow_by_inst, instruments_seen = _collect_lens_hits(
        per_lens, ("myeongni", "market_myeongni")
    )

    chain_scores = chain.get("scores") if isinstance(chain.get("scores"), dict) else {}
    market_scores = market.get("scores") if isinstance(market.get("scores"), dict) else {}
    overlay = market.get("overlay") if isinstance(market.get("overlay"), dict) else {}

    separation_ok = bool(market.get("schema") == "market_myeongni_lens_v1")
    warnings: List[str] = []
    if not chain:
        warnings.append("missing myeongni_independent_lens_from_chain_latest.json")
    if not market:
        warnings.append("missing market_myeongni_lens_latest.json (run run_market_myeongni_lens_v1.py)")

    doc = {
        "schema": "myeongni_lens_observation_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hypothesis_tier": "B",
        "research_only": True,
        "not_hit_rate_proof": True,
        "separation": {
            "birth_chain_lens": "myeongni_independent_lens_from_chain_latest.json",
            "market_overlay_lens": "market_myeongni_lens_latest.json",
            "auto_merge_forbidden": True,
            "market_replaces_birth_chart": False,
            "overlay_policy_applied": overlay.get("policy_id") or market.get("policy_path"),
        },
        "snapshots": {
            "chain_direction_score": chain_scores.get("direction_score"),
            "chain_direction_ko": _ko_dir(chain_scores.get("direction_score")),
            "chain_confidence": chain_scores.get("confidence"),
            "market_direction_score": market_scores.get("direction_score"),
            "market_direction_ko": _ko_dir(market_scores.get("direction_score")),
            "v0_lens_direction_score": (lens.get("scores") or {}).get("direction_score"),
        },
        "gates": {
            "shadow_decision": gate.get("decision"),
            "stage2_realset_pass": stage2.get("pass"),
            "stage2_real_count": stage2.get("real_count"),
            "promotion_status": promo.get("status"),
            "promotion_decision": promo.get("decision"),
        },
        "fusion_context": {
            "agreement_rate": (gate.get("latest_consensus") or {}).get("agreement_rate"),
            "minority_lens_ids": (gate.get("latest_conflict_snapshot") or {}).get("minority_lens_ids"),
        },
        "shadow_price_hits": shadow_hits,
        "shadow_price_hits_by_instrument": shadow_by_inst,
        "shadow_price_hit": shadow_hits.get("myeongni"),
        "instruments_seen": instruments_seen,
        "shadow_counterfactual": True,
        "d_validation_note_ko": (
            "시장 적중률 헤드라인 없음. shadow_price_hits는 per-lens 벤치 스냅샷(반사실)이며 "
            "출생 체인 vs 시장 오버레이 분리·게이트 스냅샷과 별도."
        ),
        "warnings": warnings,
        "separation_contract_ok": separation_ok and bool(chain),
    }
    return doc


def write_report(workspace: Path | None = None) -> tuple[Path, Path]:
    ws = (workspace or ROOT).resolve()
    doc = build_myeongni_lens_observation_report(ws)
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 명리 관측 리포트 v1 (분리 계약)",
        "",
        f"- generated: {doc['generated_at_utc']}",
        "- `[HYPO]` · `research_only` · **적중률 증명 아님**",
        "",
        "## 분리",
        f"- 출생 체인: `{doc['separation']['birth_chain_lens']}`",
        f"- 시장 오버레이: `{doc['separation']['market_overlay_lens']}`",
        f"- 시장이 사주를 **치환하지 않음**: {doc['separation']['market_replaces_birth_chart']}",
        "",
        "## 스냅샷",
        f"- chain direction: {doc['snapshots']['chain_direction_ko']} ({doc['snapshots']['chain_direction_score']})",
        f"- market overlay direction: {doc['snapshots']['market_direction_ko']} ({doc['snapshots']['market_direction_score']})",
        "",
        "## 게이트",
        f"- shadow: {doc['gates']['shadow_decision']}",
        f"- stage2 realset: pass={doc['gates']['stage2_realset_pass']} n={doc['gates']['stage2_real_count']}",
        f"- promotion: {doc['gates']['promotion_decision']}",
        "",
        "## Shadow hit (counterfactual · not headline)",
    ]
    for lid, per_inst in (doc.get("shadow_price_hits_by_instrument") or {}).items():
        for inst, row in (per_inst or {}).items():
            lines.append(
                f"- {lid} · {inst}: hit={row.get('price_directional_hit_rate')} "
                f"n={row.get('n_evaluated')}"
            )
    lines.extend(["", doc["d_validation_note_ko"]])
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return OUT_JSON, OUT_MD


def main() -> int:
    j, m = write_report()
    print(f"WROTE: {j}")
    print(f"WROTE: {m}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
