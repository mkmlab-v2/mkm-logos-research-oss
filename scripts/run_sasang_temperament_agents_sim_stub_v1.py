#!/usr/bin/env python3
"""RQ-026 closed-loop sasang temperament 4-agent sim stub ([HYPO]).

Reads market psych v2 byungjeung rows as environment input only.
Outputs temperament/consensus logs — no price, compression, or trading rails.
"""
from __future__ import annotations

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SPEC = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/temperament_agent_state_v1.example.json"
)
DEFAULT_MATRIX = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_2.json"
)
DEFAULT_MATRIX_BASELINE = (
    ROOT / "experiments/sasang_temperament_agents_v1/specs/pathology_transition_matrix_v1_1.json"
)
DEFAULT_INPUT = ROOT / "reports/btrack_per_date_directions_market_psych_v2.json"
DEFAULT_OUT = ROOT / "reports/sasang_temperament_agents_sim_v1_latest.json"

FORBIDDEN_OUTPUT_KEYS = frozenset(
    {
        "price_directional_hit_rate",
        "jaccard",
        "saving_pct",
        "global_saving",
        "predicted_direction",
        "actual_direction",
        "order_action",
        "live_trading",
    }
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _agent_index(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {str(a["constitution_id"]): a for a in spec.get("agents") or []}


def _init_states(spec: dict[str, Any]) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    for agent in spec.get("agents") or []:
        cid = str(agent["constitution_id"])
        seed = agent.get("temperament_seed") or {}
        out[cid] = {
            "absorption": float(seed.get("absorption", 0.5)),
            "dispersion": float(seed.get("dispersion", 0.5)),
            "pathology_scalar": float(seed.get("pathology_scalar", 0.1)),
            "stress_internal": 0.0,
        }
    return out


def _affinity_multiplier(matrix: dict[str, Any] | None, agent: dict[str, Any]) -> float:
    if not matrix:
        return 1.0
    cid = str(agent.get("constitution_id") or "")
    primary = str(agent.get("primary_pathology_sim") or "")
    aff_map = (matrix.get("constitution_pathology_affinity") or {}).get(cid) or {}
    if primary in aff_map:
        return float(aff_map[primary])
    if aff_map:
        return float(max(aff_map.values()))
    return 1.0


def _hint_pathology_gain(matrix: dict[str, Any] | None, hint: str) -> float:
    if not matrix:
        return 1.0
    mod = (matrix.get("hint_modifiers") or {}).get(hint) or {}
    return float(mod.get("pathology_gain", 1.0))


def _apply_transition(
    *,
    state: dict[str, float],
    agent: dict[str, Any],
    hint: str,
    stress_index: float,
    stress_delta: float,
    rules: dict[str, Any],
    matrix: dict[str, Any] | None = None,
) -> dict[str, float]:
    rule = rules.get(hint) or rules.get("stable_transition") or {}
    scale = float(rule.get("pathology_delta_scale", 0.05))
    coupling = float(rule.get("stress_coupling", 0.5))
    absorp = float(agent.get("temperament_seed", {}).get("absorption", 0.5))
    dispers = float(agent.get("temperament_seed", {}).get("dispersion", 0.5))
    drive = abs(stress_delta) * coupling + stress_index * 0.15
    affinity = _affinity_multiplier(matrix, agent)
    hint_gain = _hint_pathology_gain(matrix, hint)
    temperament_mix = 0.6 * absorp + 0.4 * dispers
    if hint == "aggravating":
        delta = scale * drive * temperament_mix * max(0.05, hint_gain) * affinity
        state["pathology_scalar"] = _clamp(state["pathology_scalar"] + delta)
        state["stress_internal"] = _clamp(state["stress_internal"] + delta * 0.8)
    elif hint == "recovering":
        delta = scale * drive * (0.5 * absorp + 0.5 * dispers) * abs(hint_gain) * affinity
        state["pathology_scalar"] = _clamp(state["pathology_scalar"] - delta)
        state["stress_internal"] = _clamp(state["stress_internal"] - delta * 0.7)
    else:
        delta = scale * drive * 0.25 * max(0.05, abs(hint_gain)) * affinity
        state["pathology_scalar"] = _clamp(state["pathology_scalar"] + (delta - scale * 0.5) * 0.1)
        state["stress_internal"] = _clamp(state["stress_internal"] + (stress_delta * 0.05))
    return state


def _conflict_score(pathology_values: list[float]) -> float:
    if len(pathology_values) < 2:
        return 0.0
    return float(statistics.pstdev(pathology_values))


def _transition_replay_ok(hint: str, before: float, after: float, eps: float = 1e-9) -> bool:
    d = after - before
    if hint == "aggravating":
        return d >= -eps
    if hint == "recovering":
        return d <= eps
    return abs(d) <= 0.08


def run_sim(
    *,
    spec: dict[str, Any],
    env_rows: list[dict[str, Any]],
    max_days: int | None,
    matrix: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rules = spec.get("stress_transitions") or {}
    threshold = float((spec.get("consensus") or {}).get("conflict_score_threshold", 0.22))
    agents = spec.get("agents") or []
    by_id = _agent_index(spec)
    states = _init_states(spec)

    rows = sorted(env_rows, key=lambda r: str(r.get("eval_date") or ""))
    if max_days is not None and max_days > 0:
        rows = rows[:max_days]

    daily_steps: list[dict[str, Any]] = []
    consensus_log: list[dict[str, Any]] = []
    replay_hits = 0
    replay_total = 0
    conflict_scores: list[float] = []
    consensus_days = 0

    for row in rows:
        bj = row.get("byungjeung") or {}
        hint = str(bj.get("transition_hint") or "stable_transition")
        stress_index = float(bj.get("stress_index") or 0.0)
        stress_delta = float(bj.get("stress_delta") or 0.0)
        eval_date = str(row.get("eval_date") or "")

        agent_snapshots: list[dict[str, Any]] = []

        for agent in agents:
            cid = str(agent["constitution_id"])
            prev = states[cid]["pathology_scalar"]
            states[cid] = _apply_transition(
                state=states[cid],
                agent=agent,
                hint=hint,
                stress_index=stress_index,
                stress_delta=stress_delta,
                rules=rules,
                matrix=matrix,
            )
            after = states[cid]["pathology_scalar"]
            replay_total += 1
            if _transition_replay_ok(hint, prev, after):
                replay_hits += 1
            agent_snapshots.append(
                {
                    "constitution_id": cid,
                    "pathology_scalar": round(after, 6),
                    "primary_pathology_sim": agent.get("primary_pathology_sim"),
                    "transition_replay_ok": _transition_replay_ok(hint, prev, after),
                }
            )

        path_vals = [states[str(a["constitution_id"])]["pathology_scalar"] for a in agents]
        conflict = _conflict_score(path_vals)
        conflict_scores.append(conflict)
        consensus = conflict <= threshold
        if consensus:
            consensus_days += 1
        dominant = max(
            (str(a["constitution_id"]) for a in agents),
            key=lambda c: states[c]["pathology_scalar"],
        )

        step = {
            "eval_date": eval_date,
            "environment": {
                "transition_hint": hint,
                "stress_index": round(stress_index, 6),
                "stress_delta": round(stress_delta, 6),
                "byungjeung_state": bj.get("byungjeung_state"),
            },
            "agents": agent_snapshots,
            "conflict_score": round(conflict, 6),
            "consensus_day": consensus,
            "dominant_pathology_agent": dominant,
        }
        daily_steps.append(step)
        consensus_log.append(
            {
                "eval_date": eval_date,
                "consensus_day": consensus,
                "conflict_score": round(conflict, 6),
                "dominant_pathology_agent": dominant,
                "pathology_rank": sorted(
                    ((cid, round(states[cid]["pathology_scalar"], 6)) for cid in states),
                    key=lambda x: x[1],
                    reverse=True,
                ),
            }
        )

    n = len(daily_steps) or 1
    mean_conflict = sum(conflict_scores) / n if conflict_scores else 0.0
    temperament_consistency = round(_clamp(1.0 - mean_conflict, 0.0, 1.0), 6)
    pathology_replay_rate = round(replay_hits / replay_total, 6) if replay_total else 0.0

    return {
        "schema": "sasang_temperament_agents_sim_report_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "rq_id": "RQ-026",
        "boundary_ack": True,
        "not_promoted_track_a": True,
        "naming_firewall_ko": (spec.get("naming_firewall") or {}).get("note_ko"),
        "inputs": {
            "spec_schema": spec.get("schema"),
            "environment_source": "market_psych_v2_byungjeung",
            "n_days_simulated": len(daily_steps),
            "pathology_matrix_schema": (matrix or {}).get("schema"),
            "pathology_matrix_coupled": matrix is not None,
        },
        "daily_steps": daily_steps,
        "consensus_log": consensus_log,
        "eval_axes": {
            "temperament_consistency": {
                "score": temperament_consistency,
                "mean_conflict_score": round(mean_conflict, 6),
                "consensus_day_rate": round(consensus_days / n, 6),
                "note_ko": "내부 4-agent pathology 분산 역수; OHLCV·Jaccard 아님.",
            },
            "pathology_transition_replay": {
                "replay_match_rate": pathology_replay_rate,
                "replay_hits": replay_hits,
                "replay_total": replay_total,
                "note_ko": "aggravating↑ recovering↓ stable≈flat 규칙 재현율; 임상 진단 아님.",
            },
        },
        "final_agent_states": {
            cid: {k: round(v, 6) for k, v in st.items()} for cid, st in states.items()
        },
    }


def _assert_no_forbidden_keys(obj: Any, path: str = "") -> None:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k in FORBIDDEN_OUTPUT_KEYS:
                raise ValueError(f"forbidden output key at {path}.{k}")
            _assert_no_forbidden_keys(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            _assert_no_forbidden_keys(item, f"{path}[{i}]")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spec", type=Path, default=DEFAULT_SPEC)
    ap.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--matrix", type=Path, default=DEFAULT_MATRIX, help="pathology matrix JSON (omit with --no-matrix)")
    ap.add_argument("--no-matrix", action="store_true", help="legacy transition without matrix coupling")
    ap.add_argument("--max-days", type=int, default=0, help="0 = all rows")
    args = ap.parse_args()

    if not args.spec.is_file():
        raise SystemExit(f"spec missing: {args.spec}")
    if not args.input.is_file():
        raise SystemExit(f"input missing: {args.input}")
    matrix_doc: dict[str, Any] | None = None
    if not args.no_matrix:
        if not args.matrix.is_file():
            raise SystemExit(f"matrix missing: {args.matrix} (use --no-matrix to skip)")
        matrix_doc = _load_json(args.matrix)

    spec = _load_json(args.spec)
    env_doc = _load_json(args.input)
    rows = [r for r in env_doc.get("rows") or [] if isinstance(r, dict)]
    if not rows:
        raise SystemExit("no environment rows")

    max_days = None if args.max_days == 0 else args.max_days
    report = run_sim(spec=spec, env_rows=rows, max_days=max_days, matrix=matrix_doc)
    _assert_no_forbidden_keys(report)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
