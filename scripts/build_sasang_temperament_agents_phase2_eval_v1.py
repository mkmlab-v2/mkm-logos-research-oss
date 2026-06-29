#!/usr/bin/env python3
"""RQ-026 phase-2: eval-axis separation gate + pathology dominance metrics ([HYPO])."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/temperament_eval_axes_contract_v1.json"
)
DEFAULT_MATRIX = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_2.json"
)
DEFAULT_SIM = ROOT / "reports/sasang_temperament_agents_sim_v1_latest.json"
DEFAULT_README = ROOT / "experiments/sasang_temperament_agents_v1/README.md"
DEFAULT_OUT = ROOT / "reports/sasang_temperament_agents_phase2_eval_v1_latest.json"
ARTIFACT_OUT = (
    ROOT / "docs/final/artifacts/sasang_temperament_agents_phase2_eval_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _walk_keys(obj: Any, keys: set[str]) -> None:
    if isinstance(obj, dict):
        keys.update(obj.keys())
        for v in obj.values():
            _walk_keys(v, keys)
    elif isinstance(obj, list):
        for item in obj:
            _walk_keys(item, keys)


def _check_forbidden_keys(sim: dict[str, Any], forbidden: list[str]) -> list[str]:
    found: set[str] = set()
    _walk_keys(sim, found)
    return sorted(k for k in forbidden if k in found)


def _check_narrative_phrases(readme_text: str, phrases: list[str]) -> list[str]:
    hits = [p for p in phrases if p in readme_text]
    return hits


def _dominance_metrics(sim: dict[str, Any], matrix: dict[str, Any]) -> dict[str, Any]:
    return dominance_metrics_from_steps(sim.get("daily_steps") or [], matrix)


def dominance_metrics_from_steps(
    steps: list[dict[str, Any]], matrix: dict[str, Any]
) -> dict[str, Any]:
    affinity = matrix.get("constitution_pathology_affinity") or {}
    rules = matrix.get("dominance_rules") or {}
    fear_ids = {"taeeum", "soeumin"}
    agg_days = 0
    fear_dominant_on_agg = 0
    pathology_label_match = 0
    pathology_label_total = 0

    for step in steps:
        env = step.get("environment") or {}
        hint = str(env.get("transition_hint") or "")
        dominant = str(step.get("dominant_pathology_agent") or "")
        agents = step.get("agents") or []
        by_id = {str(a.get("constitution_id")): a for a in agents if isinstance(a, dict)}

        if hint == "aggravating":
            agg_days += 1
            if dominant in fear_ids:
                fear_dominant_on_agg += 1

        if dominant in by_id:
            aff = affinity.get(dominant) or {}
            primary = str(by_id[dominant].get("primary_pathology_sim") or "")
            if aff:
                pathology_label_total += 1
                best = max(aff.items(), key=lambda kv: kv[1])[0]
                if primary == best or (primary in aff and aff.get(primary, 0) >= aff.get(best, 0) * 0.95):
                    pathology_label_match += 1

    min_share = float(rules.get("taeeum_or_soeumin_fear_share_on_aggravating_min", 0.45))
    fear_share = (fear_dominant_on_agg / agg_days) if agg_days else 0.0
    label_rate = (pathology_label_match / pathology_label_total) if pathology_label_total else 0.0

    return {
        "aggravating_days": agg_days,
        "fear_constitution_dominant_on_aggravating_rate": round(fear_share, 6),
        "fear_dominance_threshold": min_share,
        "fear_dominance_pass": fear_share >= min_share if agg_days else None,
        "pathology_label_affinity_match_rate": round(label_rate, 6),
        "note_ko": "태음/소음 fear sim 우세율; 임상·예측력 아님.",
    }


def build(
    *,
    contract: dict[str, Any],
    matrix: dict[str, Any],
    sim: dict[str, Any],
    readme_text: str,
) -> dict[str, Any]:
    forbidden_hits = _check_forbidden_keys(sim, list(contract.get("forbidden_metric_keys") or []))
    narrative_hits = _check_narrative_phrases(
        readme_text, list(contract.get("forbidden_narrative_phrases_ko") or [])
    )
    allowed = set(contract.get("allowed_eval_axis_ids") or [])
    eval_axes = sim.get("eval_axes") or {}
    extra_axes = sorted(set(eval_axes.keys()) - allowed)

    dominance = _dominance_metrics(sim, matrix)
    separation_ok = not forbidden_hits and not narrative_hits and not extra_axes

    doc = {
        "schema": "sasang_temperament_agents_phase2_eval_v1",
        "generated_at_utc": _utc(),
        "rq_id": "RQ-026",
        "hypothesis_tier": "B",
        "research_only": True,
        "not_promoted_track_a": True,
        "eval_separation_ok": separation_ok,
        "checks": {
            "forbidden_metric_keys_in_sim": forbidden_hits,
            "forbidden_narrative_phrases_in_readme": narrative_hits,
            "unexpected_eval_axis_ids": extra_axes,
            "allowed_eval_axis_ids": sorted(allowed),
        },
        "sim_eval_axes_snapshot": {
            k: eval_axes.get(k) for k in sorted(eval_axes.keys()) if k in allowed
        },
        "eval_axes": {
            **{k: eval_axes[k] for k in eval_axes if k in allowed},
            "constitution_pathology_dominance": dominance,
        },
        "contract_pointer": str(DEFAULT_CONTRACT.relative_to(ROOT)).replace("\\", "/"),
        "matrix_pointer": str(DEFAULT_MATRIX.relative_to(ROOT)).replace("\\", "/"),
        "verdict_ko": (
            "phase2 eval 분리 OK; constitution pathology dominance 기록됨. research_only·승격 없음."
            if separation_ok
            else "phase2 eval 분리 FAIL — forbidden key/phrase/axis 확인."
        ),
    }
    return doc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    ap.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX)
    ap.add_argument("--sim", type=Path, default=DEFAULT_SIM)
    ap.add_argument("--readme", type=Path, default=DEFAULT_README)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--also-artifact", action="store_true")
    ap.add_argument("--strict", action="store_true", help="exit 1 if eval_separation_ok false")
    args = ap.parse_args()

    for p, name in (
        (args.contract, "contract"),
        (args.matrix, "matrix"),
        (args.sim, "sim"),
        (args.readme, "readme"),
    ):
        if not p.is_file():
            raise SystemExit(f"missing {name}: {p}")

    doc = build(
        contract=_load(args.contract),
        matrix=_load(args.matrix),
        sim=_load(args.sim),
        readme_text=args.readme.read_text(encoding="utf-8"),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    if args.also_artifact:
        ARTIFACT_OUT.parent.mkdir(parents=True, exist_ok=True)
        ARTIFACT_OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(ARTIFACT_OUT)
    if args.strict and not doc.get("eval_separation_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
