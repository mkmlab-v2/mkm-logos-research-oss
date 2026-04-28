#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build symbolic topology insight packet (v1).")
    ap.add_argument("--seed-symbol", default="tree_of_knowledge_good_evil")
    ap.add_argument(
        "--survivor-json",
        default="docs/final/artifacts/insight_survivor_candidates_latest.json",
    )
    ap.add_argument(
        "--meaning-json",
        default="docs/final/artifacts/bible_meaning_insight_candidates_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/symbolic_topology_insight_latest.json",
    )
    args = ap.parse_args()

    sp = resolve(args.survivor_json)
    mp = resolve(args.meaning_json)
    op = resolve(args.output_json)

    survivors = load_json(sp) if sp.is_file() else {}
    meaning = load_json(mp) if mp.is_file() else {}

    sv = survivors.get("survivors") if isinstance(survivors.get("survivors"), list) else []
    top = sv[0] if sv else {}
    top_summary = top.get("source_summary") if isinstance(top.get("source_summary"), dict) else {}
    candidate_count = len(meaning.get("candidates") or []) if isinstance(meaning.get("candidates"), list) else 0

    # Symbolic topology axes (0~1) for "Tree of Knowledge of Good and Evil"
    axes = {
        "boundary_obedience_vs_autonomy": 0.86,
        "desire_intensity": 0.81,
        "epistemic_acceleration": 0.77,
        "self_grounding_vs_transcendence": 0.84,
        "shame_fragmentation": 0.72,
    }

    # Operational coupling from current survivor/meaning context.
    ci_low = float(top.get("ci_low_defense_contrib", 0.0) or 0.0)
    fusion_score = float(top.get("fusion_candidate_score", 0.0) or 0.0)
    risk_bias = clamp01(0.5 * axes["self_grounding_vs_transcendence"] + 0.5 * axes["desire_intensity"])
    discipline_bias = clamp01(0.5 * ci_low + 0.5 * (1.0 - axes["shame_fragmentation"]))
    expansion_pressure = clamp01(0.5 * axes["epistemic_acceleration"] + 0.5 * fusion_score)

    # Our own expansion rules (symbol -> modern domains).
    expansion_rules = [
        {
            "rule_id": "R1_boundary_violation_loop",
            "if_symbolic_pattern": "desire exceeds covenant boundary",
            "modern_mapping": "risk_limit_overwrite / policy bypass pressure",
            "expected_signal": "short-term upside temptation, long-tail drawdown risk",
            "governance_link": "activate fail-boundary gate before promotion",
        },
        {
            "rule_id": "R2_epistemic_shortcut",
            "if_symbolic_pattern": "knowledge seized without maturation path",
            "modern_mapping": "model-overconfidence under sparse validation",
            "expected_signal": "apparent precision with hidden fragility",
            "governance_link": "require falsification + sensitivity breakpoint disclosure",
        },
        {
            "rule_id": "R3_shame_fragmentation",
            "if_symbolic_pattern": "post-transgression identity split",
            "modern_mapping": "lens disagreement / conflict ratio jump",
            "expected_signal": "regime instability and defensive posture shift",
            "governance_link": "dynamic cap tightening + rollback semantics",
        },
    ]

    symbolic_bridges = [
        {
            "from_symbol": "tree_of_knowledge_good_evil",
            "to_regime_tag": "empire_transition",
            "bridge_type": "boundary_to_regime_instability",
            "supporting_node": top_summary.get("source_node_id", "unknown"),
            "supporting_candidate_id": top_summary.get("candidate_id", "unknown"),
            "support_strength": clamp01((ci_low + fusion_score) / 2.0),
        }
    ]

    out = {
        "schema": "symbolic_topology_insight_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "seed_symbol": args.seed_symbol,
        "symbolic_topology_axes": axes,
        "operational_coupling": {
            "risk_bias": risk_bias,
            "discipline_bias": discipline_bias,
            "expansion_pressure": expansion_pressure,
            "survivor_ci_low_defense_contrib": ci_low,
            "survivor_fusion_candidate_score": fusion_score,
            "meaning_candidate_count": candidate_count,
        },
        "expansion_rules": expansion_rules,
        "symbolic_bridges": symbolic_bridges,
        "narrative_interpretation_ko": {
            "core": "선악과는 '지식' 자체보다 경계 위반을 통한 자기-근거화 충동의 상징으로 해석된다.",
            "topology": "위상좌표상 경계/자율, 욕망강도, 자기근거화 축이 동시에 높은 상태는 시스템의 조기 승격 압력과 결합된다.",
            "modern_extension": "현대 운영에서는 정책 우회·과신·렌즈 충돌로 나타나며, fail-boundary 게이트를 통과하지 못하면 승격을 보류해야 한다.",
        },
        "sources": {
            "survivor_json": str(sp) if sp.is_file() else None,
            "meaning_json": str(mp) if mp.is_file() else None,
        },
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

