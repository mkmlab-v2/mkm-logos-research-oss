#!/usr/bin/env python3
"""L1 lane inject → L2 Trust Packet compress chain pilot (tp01 + lane SSOT).

[HYPO] / research_only / B-track. Human resume MD unchanged; not Track A SLA.

  py scripts/build_a2a_l1_l2_chain_pilot_v1.py
  py scripts/build_a2a_l1_l2_chain_pilot_v1.py --lane infra --strict-exit
  py scripts/build_a2a_l1_l2_chain_pilot_v1.py --all-lanes
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
sys.path.insert(0, str(ROOT / "scripts"))

from bench_mkm_ltm_resume_lane_token_v1 import (  # noqa: E402
    _count_tokens,
    _lane_inject_text,
    _naive_baseline_text,
)
from mkm_a2a_compress_pilot_lib_v1 import (  # noqa: E402
    compress_plaintext_v2,
    load_compress_skip_rules,
)
from mkm_ops_memory_index_lib_v1 import DEFAULT_INDEX_PATH, LANE_OPS_PACKS  # noqa: E402

DEFAULT_OUT = ROOT / "docs/final/artifacts/a2a_l1_l2_chain_pilot_v1_latest.json"
DEFAULT_LOG = ROOT / "docs/final/artifacts/a2a_l1_l2_chain_pilot_log.jsonl"
STUB_KEY = "mk_stub_v2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _stub_jaccard(packet: dict[str, Any] | None) -> float | None:
    if not isinstance(packet, dict):
        return None
    stub = (packet.get("residual_meta") or {}).get(STUB_KEY) or {}
    j = stub.get("reconstruction_fidelity_jaccard")
    return float(j) if isinstance(j, (int, float)) else None


def _run_lane_chain(
    root: Path,
    *,
    lane: str,
    naive_tokens: int,
    min_tokens: int,
    routing_profile: str,
    client: Any,
) -> dict[str, Any]:
    inject_text = _lane_inject_text(root, lane)
    inject_count = _count_tokens(inject_text)
    inject_t = int(inject_count["tokens"])
    l1_saved = max(0, naive_tokens - inject_t)
    l1_ratio = round(l1_saved / naive_tokens, 6) if naive_tokens else 0.0

    compress_row = compress_plaintext_v2(
        client,
        inject_text,
        min_tokens=min_tokens,
        routing_profile=routing_profile,
        client_request_id=f"a2a-l1-l2-{lane}",
    )

    decision = compress_row.get("decision")
    metrics = compress_row.get("compression_metrics") or {}
    token_out = metrics.get("token_out")
    wire_savings = metrics.get("savings_ratio")
    packet = compress_row.get("trust_packet_redacted")

    end_to_end_tokens = inject_t
    end_to_end_note = "L2 skipped — wire carries inject pins only"
    if decision == "compressed" and isinstance(token_out, int):
        end_to_end_tokens = int(token_out)
        end_to_end_note = "naive baseline vs v2 compress token_out on inject"
    elif decision == "compressed" and token_out is not None:
        end_to_end_tokens = int(token_out)
        end_to_end_note = "naive baseline vs v2 compress token_out on inject"

    e2e_saved = max(0, naive_tokens - end_to_end_tokens)
    e2e_ratio = round(e2e_saved / naive_tokens, 6) if naive_tokens else 0.0

    expand = compress_row.get("expand_packet_only") or {}
    lane_ok = bool(inject_t > 0)
    if decision == "compressed":
        lane_ok = lane_ok and compress_row.get("http_status") == 200 and expand.get("http_status") == 200
    elif decision == "skipped_below_min_tokens":
        lane_ok = lane_ok  # documented skip is OK for pilot
    else:
        lane_ok = False

    return {
        "lane": lane,
        "lane_ok": lane_ok,
        "node_ids": list(LANE_OPS_PACKS.get(lane) or []),
        "l1_skim_inject": {
            "inject_tokens": inject_t,
            "token_count_method": inject_count.get("method"),
            "char_count": len(inject_text),
            "naive_baseline_tokens": naive_tokens,
            "tokens_saved_vs_naive": l1_saved,
            "savings_ratio_vs_naive": l1_ratio,
            "preview_head": inject_text[:200] + ("..." if len(inject_text) > 200 else ""),
        },
        "l2_a2a_compress": compress_row,
        "stub_jaccard": _stub_jaccard(
            compress_row.get("trust_packet_redacted")
            if isinstance(compress_row.get("trust_packet_redacted"), dict)
            else None
        ),
        "chain_kpi": {
            "l1_savings_ratio_vs_naive": l1_ratio,
            "l2_savings_ratio_on_inject": wire_savings,
            "end_to_end_tokens_vs_naive": end_to_end_tokens,
            "end_to_end_savings_ratio_vs_naive": e2e_ratio,
            "end_to_end_note": end_to_end_note,
        },
    }


def build_chain_document(
    root: Path,
    *,
    lanes: list[str],
    routing_profile: str = "track_a_promoted",
) -> dict[str, Any]:
    skip_rules = load_compress_skip_rules(root)
    min_tokens = int(skip_rules.get("min_plaintext_tokens_recommend") or 32)

    naive_text = _naive_baseline_text(root)
    naive_count = _count_tokens(naive_text)
    naive_t = int(naive_count["tokens"])

    from fastapi.testclient import TestClient

    from scripts.compression_token_api_v2_stub import app

    client = TestClient(app)
    lane_rows = [
        _run_lane_chain(
            root,
            lane=lane,
            naive_tokens=naive_t,
            min_tokens=min_tokens,
            routing_profile=routing_profile,
            client=client,
        )
        for lane in lanes
    ]

    chain_ok = all(r.get("lane_ok") for r in lane_rows)
    compressed_lanes = [
        r for r in lane_rows if (r.get("l2_a2a_compress") or {}).get("decision") == "compressed"
    ]

    return {
        "schema": "a2a_l1_l2_chain_pilot_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "classification": "INTERNAL_ONLY",
        "target_point_id": "tp01_cursor_ops_resume_handoff",
        "chain_id": "l1_lane_inject_l2_trust_packet_v1",
        "status": "PILOT",
        "chain_ok": chain_ok,
        "boundary_ack": (
            "[HYPO] L1 lane inject pins then L2 v2 Trust Packet compress when inject >= min_tokens. "
            "Not coordinate-only handoff. Not lossless understanding. Not Track A SLA."
        ),
        "a2a_target_points_ssot": "docs/final/artifacts/a2a_target_points_v1_latest.json",
        "lane_bench_ssot": "reports/mkm_ltm_resume_lane_token_bench_v1_latest.json",
        "options": {
            "lanes": lanes,
            "routing_profile": routing_profile,
            "min_plaintext_tokens": min_tokens,
        },
        "naive_baseline": {
            "sources": ["MISSION_LOG.md", "docs/final/CENTRAL_AGENT_MEMORY_V1.md"],
            **naive_count,
        },
        "compress_skip_rules_applied": skip_rules,
        "lanes": lane_rows,
        "aggregate": {
            "lane_count": len(lane_rows),
            "compressed_lane_count": len(compressed_lanes),
            "all_lanes_ok": chain_ok,
            "mean_l1_savings_ratio": (
                round(
                    sum(r["chain_kpi"]["l1_savings_ratio_vs_naive"] for r in lane_rows) / len(lane_rows),
                    6,
                )
                if lane_rows
                else None
            ),
            "mean_l2_savings_on_inject": (
                round(
                    sum(
                        (r["l2_a2a_compress"].get("compression_metrics") or {}).get("savings_ratio") or 0.0
                        for r in compressed_lanes
                    )
                    / len(compressed_lanes),
                    6,
                )
                if compressed_lanes
                else None
            ),
            "mean_end_to_end_savings_vs_naive": (
                round(
                    sum(r["chain_kpi"]["end_to_end_savings_ratio_vs_naive"] for r in lane_rows) / len(lane_rows),
                    6,
                )
                if lane_rows
                else None
            ),
        },
        "wire_handoff_hint": {
            "step_1": "L1: lane inject pins (essence + must_keep_tags) — original files stay on disk",
            "step_2": "L2: if inject_tokens >= min_tokens, POST /v2/compress → trust_packet to peer agent",
            "step_3": "peer: POST /v2/expand packet-only — not full MISSION/CENTRAL paste",
            "human_ui_unchanged": "docs/final/artifacts/mkm_chat_resume_pack_latest.md",
        },
        "evidence_paths": [
            "scripts/build_a2a_l1_l2_chain_pilot_v1.py",
            "scripts/bench_mkm_ltm_resume_lane_token_v1.py",
            "scripts/mkm_a2a_compress_pilot_lib_v1.py",
            "scripts/compression_token_api_v2_stub.py",
        ],
    }


def _append_log(log_path: Path, doc: dict[str, Any]) -> None:
    row = {
        "schema": "a2a_l1_l2_chain_pilot_log_v1",
        "measured_at_utc": doc.get("generated_at_utc"),
        "chain_ok": doc.get("chain_ok"),
        "aggregate": doc.get("aggregate"),
    }
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lane", action="append", choices=sorted(LANE_OPS_PACKS.keys()))
    ap.add_argument("--all-lanes", action="store_true")
    ap.add_argument(
        "--routing-profile",
        default="track_a_promoted",
        choices=["default", "track_a_promoted", "b_track_domain_relax"],
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--append-log", action="store_true")
    ap.add_argument("--strict-exit", action="store_true")
    args = ap.parse_args()

    if not DEFAULT_INDEX_PATH.is_file():
        print("FAIL: ops index missing — run build_mkm_ops_memory_index_v1.py", file=sys.stderr)
        return 1

    if args.all_lanes:
        lanes = sorted(LANE_OPS_PACKS.keys())
    elif args.lane:
        lanes = args.lane
    else:
        lanes = ["infra", "ms"]

    doc = build_chain_document(ROOT, lanes=lanes, routing_profile=args.routing_profile)
    if args.append_log:
        _append_log(args.log, doc)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    agg = doc.get("aggregate") or {}
    print(f"WROTE: {args.out}")
    print(
        f"chain_ok={doc.get('chain_ok')} lanes={agg.get('lane_count')} "
        f"mean_l1={agg.get('mean_l1_savings_ratio')} "
        f"mean_l2={agg.get('mean_l2_savings_on_inject')} "
        f"mean_e2e={agg.get('mean_end_to_end_savings_vs_naive')}"
    )
    if args.strict_exit and not doc.get("chain_ok"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
