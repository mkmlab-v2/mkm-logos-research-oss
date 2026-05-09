#!/usr/bin/env python3
"""Append-only advisory snapshot: Role Router multiscenario opt vs S1 shadow governance.

Non-gating: research_only / advisory_only. Does not mutate apply policy, engine input,
or any live gate. Intended for Track C daily fusion observability (2-week metrics).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"

ROUTER_CANDIDATES = [
    ART / "prophecy_role_router_multiscenario_opt_30y_kospi_latest.json",
    ART / "prophecy_role_router_multiscenario_opt_v1_latest.json",
]
DEFAULT_WEEKLY = ART / "lens_penalty_shadow_weekly_report_latest.json"
DEFAULT_GATE = ART / "lens_penalty_s1_shadow_gate_latest.json"
DEFAULT_OUT_LATEST = ART / "role_router_s1_shadow_advisory_latest.json"
DEFAULT_OUT_LOG = REPORTS / "role_router_s1_shadow_advisory_log.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _pick_router_path(explicit: Path | None) -> tuple[Path | None, dict[str, Any]]:
    if explicit is not None and explicit.is_file():
        return explicit, _read_json(explicit)
    for p in ROUTER_CANDIDATES:
        if p.is_file():
            return p, _read_json(p)
    return None, {}


def _extract_best_candidate(doc: dict[str, Any]) -> dict[str, Any]:
    schema = str(doc.get("schema") or "")
    if schema != "prophecy_role_router_multiscenario_opt_v1":
        return {}
    selected = doc.get("best_candidate") if isinstance(doc.get("best_candidate"), dict) else {}
    top = doc.get("top_candidates") or []
    if isinstance(top, list):
        for cand in top:
            if isinstance(cand, dict):
                oos = cand.get("oos_metrics") or {}
                if int(oos.get("n_days") or 0) >= 20:
                    selected = cand
                    break
    return selected if isinstance(selected, dict) else {}


def _router_stance(candidate: dict[str, Any]) -> str:
    oos = candidate.get("oos_metrics") if isinstance(candidate.get("oos_metrics"), dict) else {}
    hit = float(oos.get("directional_hit_rate_active") or oos.get("directional_hit_rate") or 0.0)
    mdd = float(oos.get("mdd") or 0.0)
    sharpe = float(oos.get("sharpe") or 0.0)
    n_days = int(oos.get("n_days") or 0)
    if n_days < 20:
        return "INSUFFICIENT_DATA"
    if hit >= 0.55 and mdd >= -0.15 and sharpe > 0.0:
        return "PROPOSE_RELAX_OR_ALLOW"
    return "PROPOSE_CONSERVATIVE"


def _baseline_stance(gate: dict[str, Any]) -> str:
    d = str(gate.get("decision") or "").upper()
    if d == "GO_REVIEW":
        return "REVIEW_PATH_OPEN"
    return "CONSERVATIVE_HOLD"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--router-json", type=Path, default=None, help="Override; else first existing candidate path.")
    ap.add_argument("--weekly-json", type=Path, default=DEFAULT_WEEKLY)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--out-latest", type=Path, default=DEFAULT_OUT_LATEST)
    ap.add_argument("--out-log", type=Path, default=DEFAULT_OUT_LOG)
    args = ap.parse_args()

    router_path, router_doc = _pick_router_path(args.router_json)
    weekly = _read_json(args.weekly_json)
    gate = _read_json(args.gate_json)

    strict_gap = float(((weekly.get("summary") or {}) if isinstance(weekly.get("summary"), dict) else {}).get("strict_gap") or 0.0)
    baseline = _baseline_stance(gate)
    best = _extract_best_candidate(router_doc) if router_doc else {}
    router_stance = _router_stance(best) if best else "ROUTER_ARTIFACT_MISSING"

    agree_conservative = baseline == "CONSERVATIVE_HOLD" and router_stance == "PROPOSE_CONSERVATIVE"
    agree_explore = baseline == "REVIEW_PATH_OPEN" and router_stance == "PROPOSE_RELAX_OR_ALLOW"
    conflict_resolution_proxy = 1.0 if (agree_conservative or agree_explore) else 0.0

    false_intervention_proxy = (
        1.0
        if (baseline == "CONSERVATIVE_HOLD" and router_stance == "PROPOSE_RELAX_OR_ALLOW")
        else 0.0
    )

    strict_gap_contribution = round(strict_gap, 6)

    row = {
        "schema": "role_router_s1_shadow_advisory_row_v1",
        "ts_utc": _now(),
        "research_only": True,
        "advisory_only": True,
        "non_gating": True,
        "router_artifact": str(router_path.resolve()).replace("\\", "/") if router_path else None,
        "baseline_gate_decision": str(gate.get("decision") or "UNKNOWN"),
        "baseline_stance": baseline,
        "router_stance": router_stance,
        "weekly_strict_gap": strict_gap_contribution,
        "metrics": {
            "conflict_resolution_proxy": conflict_resolution_proxy,
            "strict_gap_contribution": strict_gap_contribution,
            "false_intervention_proxy": false_intervention_proxy,
        },
        "router_best_candidate_summary": {
            "oos_metrics": (best.get("oos_metrics") if isinstance(best.get("oos_metrics"), dict) else {}),
            "params_keys": sorted(list((best.get("params") or {}).keys()))[:12]
            if isinstance(best.get("params"), dict)
            else [],
        },
        "inputs": {
            "weekly_json": str(args.weekly_json.resolve()).replace("\\", "/"),
            "gate_json": str(args.gate_json.resolve()).replace("\\", "/"),
        },
    }

    latest = {
        "schema": "role_router_s1_shadow_advisory_v1",
        "generated_at_utc": row["ts_utc"],
        "research_only": True,
        "advisory_only": True,
        "non_gating": True,
        "last_row": row,
        "notes": [
            "conflict_resolution_proxy: 1 when baseline and router stances agree (conservative or explore).",
            "strict_gap_contribution: snapshot from lens_penalty_shadow_weekly_report summary.strict_gap.",
            "false_intervention_proxy: 1 when baseline is CONSERVATIVE_HOLD but router proposes RELAX_OR_ALLOW.",
        ],
    }

    args.out_latest.parent.mkdir(parents=True, exist_ok=True)
    args.out_latest.write_text(json.dumps(latest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    args.out_log.parent.mkdir(parents=True, exist_ok=True)
    with args.out_log.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"WROTE: {args.out_latest}")
    print(f"APPEND: {args.out_log}")
    print(
        f"router={router_stance} baseline={baseline} "
        f"resolution_proxy={conflict_resolution_proxy} false_intervention_proxy={false_intervention_proxy}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
