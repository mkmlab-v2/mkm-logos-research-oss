#!/usr/bin/env python3
"""Fixed multi-scenario A2A dialogue bench — trust-packet mock + wire-first per scenario.

[HYPO] / research_only / B-track. Repro SSOT for L2 external credibility (not Track A SLA).

  py scripts/build_a2a_dialogue_bench_v1.py
  py scripts/build_a2a_dialogue_bench_v1.py --strict-exit
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_dialogue_bench_v1_latest.json"
DEFAULT_SCENARIOS = ("trading", "health", "lexicon_dense")
DEFAULT_TURNS = 4
DEFAULT_ROUTING = "track_a_promoted"
STUB_RESIDUAL_KEY = "mk_stub_v2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mock_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    ratios: list[float] = []
    stub_jaccards: list[float] = []
    expand_jaccards: list[float] = []
    lexicon_counts: list[int] = []
    for row in summary.get("transcript") or []:
        metrics = (row.get("compress") or {}).get("compression_metrics") or {}
        if isinstance(metrics.get("savings_ratio"), (int, float)):
            ratios.append(float(metrics["savings_ratio"]))
        lc = (row.get("compress") or {}).get("lexicon_atom_id_count")
        if isinstance(lc, int):
            lexicon_counts.append(lc)
        pkt = row.get("trust_packet_redacted") or {}
        stub = (pkt.get("residual_meta") or {}).get(STUB_RESIDUAL_KEY) or {}
        if isinstance(stub.get("reconstruction_fidelity_jaccard"), (int, float)):
            stub_jaccards.append(float(stub["reconstruction_fidelity_jaccard"]))
        expand = row.get("expand_inbound_packet_only") or {}
        if isinstance(expand.get("jaccard_internal_vs_expanded"), (int, float)):
            expand_jaccards.append(float(expand["jaccard_internal_vs_expanded"]))
    return {
        "all_compress_ok": summary.get("all_compress_ok"),
        "all_expand_ok": summary.get("all_expand_ok"),
        "all_expand_packet_only": summary.get("all_expand_packet_only"),
        "savings_ratio_by_turn": ratios,
        "avg_savings_ratio": round(sum(ratios) / len(ratios), 6) if ratios else None,
        "min_savings_ratio": min(ratios) if ratios else None,
        "max_savings_ratio": max(ratios) if ratios else None,
        "zero_savings_turns": sum(1 for r in ratios if r <= 0.0),
        "avg_lexicon_atom_id_count": (
            round(sum(lexicon_counts) / len(lexicon_counts), 4) if lexicon_counts else None
        ),
        "stub_jaccard_by_turn": stub_jaccards,
        "avg_stub_jaccard": round(sum(stub_jaccards) / len(stub_jaccards), 6) if stub_jaccards else None,
        "min_stub_jaccard": min(stub_jaccards) if stub_jaccards else None,
        "expand_jaccard_by_turn": expand_jaccards,
        "avg_expand_jaccard": round(sum(expand_jaccards) / len(expand_jaccards), 6) if expand_jaccards else None,
    }


def _wire_metrics(doc: dict[str, Any]) -> dict[str, Any]:
    transcript = doc.get("transcript") or []
    savings = [
        t.get("compression_metrics_savings_ratio")
        for t in transcript
        if t.get("compression_metrics_savings_ratio") is not None
    ]
    env_vs_pkt = [
        t.get("envelope_vs_packet_savings_ratio")
        for t in transcript
        if t.get("envelope_vs_packet_savings_ratio") is not None
    ]
    return {
        "all_ok": doc.get("all_ok"),
        "avg_trust_packet_savings_ratio": doc.get("avg_trust_packet_savings_ratio"),
        "avg_envelope_vs_packet_savings": doc.get("avg_envelope_vs_packet_savings"),
        "compression_savings_ratio_by_turn": savings,
        "envelope_vs_packet_savings_by_turn": env_vs_pkt,
    }


def _scenario_row(
    *,
    scenario: str,
    turns: int,
    routing_profile: str,
) -> dict[str, Any]:
    from scripts.run_mkm_inter_agent_dialogue_mock_v1 import run_dialogue as run_mock
    from scripts.run_mkm_inter_agent_dialogue_wire_first_v1 import run_dialogue as run_wire

    mock_summary = run_mock(turns=turns, scenario=scenario, routing_profile=routing_profile)
    wire_doc = run_wire(turns=turns, scenario=scenario, routing_profile=routing_profile)
    mock_m = _mock_metrics(mock_summary)
    wire_m = _wire_metrics(wire_doc)
    ok = bool(
        mock_summary.get("all_compress_ok")
        and mock_summary.get("all_expand_ok")
        and wire_doc.get("all_ok")
    )
    return {
        "scenario": scenario,
        "scenario_ok": ok,
        "trust_packet_mock": {
            "runner": "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
            "metrics": mock_m,
        },
        "wire_first_envelope": {
            "runner": "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
            "metrics": wire_m,
        },
    }


def _routing_compare_scenario(*, turns: int, scenario: str) -> dict[str, Any]:
    from scripts.run_mkm_inter_agent_dialogue_routing_compare_v1 import run_compare

    doc = run_compare(turns=turns, scenario=scenario)
    ok = all(
        r.get("all_compress_ok") and r.get("all_expand_ok") for r in doc.get("runs") or []
    )
    runs = doc.get("runs") or []
    track_a = next((r for r in runs if r.get("routing_profile") == "track_a_promoted"), None)
    b_track = next((r for r in runs if r.get("routing_profile") == "b_track_domain_relax"), None)
    ta_avg = track_a.get("avg_savings_ratio") if track_a else None
    bt_avg = b_track.get("avg_savings_ratio") if b_track else None
    recommended = None
    if ta_avg is not None and bt_avg is not None:
        recommended = "track_a_promoted" if float(ta_avg) >= float(bt_avg) else "b_track_domain_relax"
    return {
        "scenario": scenario,
        "compare_ok": ok,
        "profiles_compared": doc.get("profiles_compared"),
        "runs": runs,
        "avg_savings_delta_b_track_minus_track_a": doc.get("avg_savings_delta_b_track_minus_track_a"),
        "recommended_routing_profile": recommended,
        "runner": "scripts/run_mkm_inter_agent_dialogue_routing_compare_v1.py",
    }


def _routing_compare_health(*, turns: int) -> dict[str, Any]:
    return _routing_compare_scenario(turns=turns, scenario="health")


def _aggregate_headline(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    avgs = [
        s["trust_packet_mock"]["metrics"].get("avg_savings_ratio")
        for s in scenarios
        if s["trust_packet_mock"]["metrics"].get("avg_savings_ratio") is not None
    ]
    stub_js = [
        s["trust_packet_mock"]["metrics"].get("avg_stub_jaccard")
        for s in scenarios
        if s["trust_packet_mock"]["metrics"].get("avg_stub_jaccard") is not None
    ]
    wire_env = [
        s["wire_first_envelope"]["metrics"].get("avg_envelope_vs_packet_savings")
        for s in scenarios
        if s["wire_first_envelope"]["metrics"].get("avg_envelope_vs_packet_savings") is not None
    ]
    return {
        "scenario_count": len(scenarios),
        "all_scenarios_ok": all(s.get("scenario_ok") for s in scenarios),
        "cross_scenario_mean_mock_avg_savings": round(sum(avgs) / len(avgs), 6) if avgs else None,
        "cross_scenario_min_mock_avg_savings": min(avgs) if avgs else None,
        "cross_scenario_max_mock_avg_savings": max(avgs) if avgs else None,
        "cross_scenario_mean_stub_jaccard": round(sum(stub_js) / len(stub_js), 6) if stub_js else None,
        "cross_scenario_mean_wire_envelope_vs_packet": round(sum(wire_env) / len(wire_env), 6) if wire_env else None,
        "avg_savings_by_scenario": {
            s["scenario"]: s["trust_packet_mock"]["metrics"].get("avg_savings_ratio") for s in scenarios
        },
    }


def build_bench_document(
    *,
    turns: int = DEFAULT_TURNS,
    routing_profile: str = DEFAULT_ROUTING,
    scenarios: tuple[str, ...] = DEFAULT_SCENARIOS,
    include_routing_compare: bool = True,
) -> dict[str, Any]:
    scenario_rows = [
        _scenario_row(scenario=sc, turns=turns, routing_profile=routing_profile) for sc in scenarios
    ]
    routing_health = _routing_compare_scenario(turns=turns, scenario="health") if include_routing_compare else None
    routing_trading = _routing_compare_scenario(turns=turns, scenario="trading") if include_routing_compare else None
    routing = None
    if include_routing_compare:
        routing = {"health": routing_health, "trading": routing_trading}
    headline = _aggregate_headline(scenario_rows)
    bench_ok = bool(
        headline["all_scenarios_ok"]
        and (routing is None or (routing_health and routing_health.get("compare_ok") and routing_trading and routing_trading.get("compare_ok")))
    )
    return {
        "schema": "a2a_dialogue_bench_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "classification": "INTERNAL_ONLY",
        "status": "PILOT",
        "bench_ok": bench_ok,
        "boundary_ack": (
            "[HYPO] Fixed multi-scenario A2A dialogue bench — trust packet mock + wire-first. "
            "Report savings and jaccard per scenario; do not merge into Track A 40-case bench or SLA."
        ),
        "repro_command": "powershell -NoProfile -ExecutionPolicy Bypass -File scripts\\Run-A2aDialogueBenchReproBundle_v1.ps1",
        "bench_config": {
            "scenarios": list(scenarios),
            "turns": turns,
            "routing_profile": routing_profile,
            "include_routing_compare_health": include_routing_compare,
            "include_routing_compare_trading": include_routing_compare,
        },
        "scenarios": scenario_rows,
        "routing_compare": routing,
        "routing_compare_health": routing_health,
        "routing_compare_trading": routing_trading,
        "kpi_headline": headline,
        "raw_vs_operational_note": (
            "stub_jaccard = base compress roundtrip; expand_jaccard = inbound packet expand vs internal plaintext. "
            "Not repair_v2 operational KPI."
        ),
        "evidence_paths": [
            "scripts/build_a2a_dialogue_bench_v1.py",
            "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
            "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
            "scripts/run_mkm_inter_agent_dialogue_routing_compare_v1.py",
            "scripts/compression_token_api_v2_stub.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=DEFAULT_TURNS)
    ap.add_argument("--routing-profile", default=DEFAULT_ROUTING)
    ap.add_argument(
        "--scenario",
        action="append",
        choices=DEFAULT_SCENARIOS,
        help="Repeat to subset scenarios (default: all three)",
    )
    ap.add_argument("--skip-routing-compare", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict-exit", action="store_true")
    args = ap.parse_args()

    scenarios = tuple(args.scenario) if args.scenario else DEFAULT_SCENARIOS
    doc = build_bench_document(
        turns=max(2, args.turns),
        routing_profile=args.routing_profile,
        scenarios=scenarios,
        include_routing_compare=not args.skip_routing_compare,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    headline = doc.get("kpi_headline") or {}
    print(f"WROTE: {args.out}")
    print(
        f"bench_ok={doc.get('bench_ok')} "
        f"cross_mean_savings={headline.get('cross_scenario_mean_mock_avg_savings')} "
        f"cross_mean_jaccard={headline.get('cross_scenario_mean_stub_jaccard')}"
    )
    if args.strict_exit and not doc.get("bench_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
