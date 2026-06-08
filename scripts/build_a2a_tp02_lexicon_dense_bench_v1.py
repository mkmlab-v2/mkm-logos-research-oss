#!/usr/bin/env python3
"""tp02 fixed bench — lexicon_dense trust-packet mock vs wire-first envelope.

[HYPO] / research_only / B-track. SSOT for tp02 ROI KPI in a2a_target_points_v1.

  py scripts/build_a2a_tp02_lexicon_dense_bench_v1.py
  py scripts/build_a2a_tp02_lexicon_dense_bench_v1.py --strict-exit
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

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_tp02_lexicon_dense_bench_v1_latest.json"
BENCH_SCENARIO = "lexicon_dense"
DEFAULT_TURNS = 4
DEFAULT_ROUTING = "track_a_promoted"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _mock_metrics(summary: dict[str, Any]) -> dict[str, Any]:
    ratios: list[float] = []
    token_ins: list[int] = []
    token_outs: list[int] = []
    for row in summary.get("transcript") or []:
        metrics = (row.get("compress") or {}).get("compression_metrics") or {}
        if isinstance(metrics.get("savings_ratio"), (int, float)):
            ratios.append(float(metrics["savings_ratio"]))
        if isinstance(metrics.get("token_in"), int):
            token_ins.append(int(metrics["token_in"]))
        if isinstance(metrics.get("token_out"), int):
            token_outs.append(int(metrics["token_out"]))
    return {
        "all_compress_ok": summary.get("all_compress_ok"),
        "all_expand_ok": summary.get("all_expand_ok"),
        "savings_ratio_by_turn": ratios,
        "token_in_by_turn": token_ins,
        "token_out_by_turn": token_outs,
        "avg_savings_ratio": round(sum(ratios) / len(ratios), 6) if ratios else None,
        "max_savings_ratio": max(ratios) if ratios else None,
        "zero_savings_turns": sum(1 for r in ratios if r <= 0.0),
    }


def _wire_metrics(doc: dict[str, Any]) -> dict[str, Any]:
    transcript = doc.get("transcript") or []
    env_bytes = [int(t.get("wire_envelope_bytes") or 0) for t in transcript]
    pkt_bytes = [int(t.get("trust_packet_json_bytes") or 0) for t in transcript]
    env_vs_pkt = [t.get("envelope_vs_packet_savings_ratio") for t in transcript if t.get("envelope_vs_packet_savings_ratio") is not None]
    savings = [t.get("compression_metrics_savings_ratio") for t in transcript if t.get("compression_metrics_savings_ratio") is not None]
    return {
        "all_ok": doc.get("all_ok"),
        "avg_trust_packet_savings_ratio": doc.get("avg_trust_packet_savings_ratio"),
        "avg_envelope_vs_packet_savings": doc.get("avg_envelope_vs_packet_savings"),
        "wire_envelope_bytes_by_turn": env_bytes,
        "trust_packet_json_bytes_by_turn": pkt_bytes,
        "envelope_vs_packet_savings_by_turn": env_vs_pkt,
        "compression_savings_ratio_by_turn": savings,
    }


def build_bench_document(
    *,
    turns: int = DEFAULT_TURNS,
    routing_profile: str = DEFAULT_ROUTING,
) -> dict[str, Any]:
    from scripts.run_mkm_inter_agent_dialogue_mock_v1 import run_dialogue as run_mock
    from scripts.run_mkm_inter_agent_dialogue_wire_first_v1 import run_dialogue as run_wire

    mock_summary = run_mock(
        turns=turns,
        scenario=BENCH_SCENARIO,
        routing_profile=routing_profile,
    )
    wire_doc = run_wire(
        turns=turns,
        scenario=BENCH_SCENARIO,
        routing_profile=routing_profile,
    )

    mock_m = _mock_metrics(mock_summary)
    wire_m = _wire_metrics(wire_doc)

    ok = bool(
        mock_summary.get("all_compress_ok")
        and mock_summary.get("all_expand_ok")
        and wire_doc.get("all_ok")
    )

    return {
        "schema": "a2a_tp02_lexicon_dense_bench_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "target_point_id": "tp02_btrack_prophecy_executor_wire",
        "status": "PILOT",
        "bench_ok": ok,
        "boundary_ack": (
            "[HYPO] tp02 lexicon_dense fixed bench — trust packet mock vs wire-first envelope. "
            "Not production A2A SLA. Not Track A trading trigger."
        ),
        "a2a_target_points_ssot": "docs/final/artifacts/a2a_target_points_v1_latest.json",
        "bench_config": {
            "scenario": BENCH_SCENARIO,
            "turns": turns,
            "routing_profile": routing_profile,
            "alpha_role": "agent_alpha_prophecy",
            "beta_role": "agent_beta_executor",
        },
        "trust_packet_mock": {
            "runner": "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
            "metrics": mock_m,
        },
        "wire_first_envelope": {
            "runner": "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
            "metrics": wire_m,
        },
        "kpi_headline": {
            "mock_avg_savings_ratio": mock_m.get("avg_savings_ratio"),
            "mock_max_savings_ratio": mock_m.get("max_savings_ratio"),
            "wire_avg_envelope_vs_packet_savings": wire_m.get("avg_envelope_vs_packet_savings"),
            "wire_avg_trust_packet_savings_ratio": wire_m.get("avg_trust_packet_savings_ratio"),
        },
        "evidence_paths": [
            "scripts/build_a2a_tp02_lexicon_dense_bench_v1.py",
            "scripts/run_mkm_inter_agent_dialogue_mock_v1.py",
            "scripts/run_mkm_inter_agent_dialogue_wire_first_v1.py",
            "scripts/compression_token_api_v2_stub.py",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--turns", type=int, default=DEFAULT_TURNS)
    ap.add_argument("--routing-profile", default=DEFAULT_ROUTING)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--strict-exit", action="store_true", help="Exit 1 if bench_ok is false")
    args = ap.parse_args()

    doc = build_bench_document(turns=max(2, args.turns), routing_profile=args.routing_profile)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    print(
        f"bench_ok={doc.get('bench_ok')} "
        f"mock_avg_savings={doc.get('kpi_headline', {}).get('mock_avg_savings_ratio')} "
        f"wire_env_vs_pkt={doc.get('kpi_headline', {}).get('wire_avg_envelope_vs_packet_savings')}"
    )
    if args.strict_exit and not doc.get("bench_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
