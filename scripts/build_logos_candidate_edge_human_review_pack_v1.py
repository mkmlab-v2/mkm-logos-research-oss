#!/usr/bin/env python3
"""Commander human-review pack for Logos candidate-edge dual-lane queue ([HYPO] B-track).

Recommended order: ANN-lite primary first, then offline_4d_knn secondary.
Does NOT set signoff approved=true or merge to canonical.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_QUEUE = ROOT / "docs/final/artifacts/logos_candidate_edge_human_review_queue_v1_latest.json"
DEFAULT_GATE_ANN = ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_gate_ann_lite_v1_latest.json"
DEFAULT_GATE_4D = ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_gate_v1_latest.json"
DEFAULT_PROMO_ANN = ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_ann_lite_v1_latest.json"
DEFAULT_PROMO_4D = ROOT / "docs/final/artifacts/logos_candidate_edge_promotion_v1_latest.json"
DEFAULT_GRAPH = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
DEFAULT_OUT_JSON = ROOT / "reports/logos_candidate_edge_human_review_pack_v1_latest.json"
DEFAULT_OUT_MD = ROOT / "reports/logos_candidate_edge_human_review_pack_v1_latest.md"
SCHEMA = "logos_candidate_edge_human_review_pack_v1"
SECONDARY_4D_SAMPLE = 20


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8-sig"))
    return obj if isinstance(obj, dict) else {}


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _promotion_pending(promo: dict[str, Any]) -> bool:
    return str(promo.get("status") or "") == "PROMOTED_TO_PENDING" and int(promo.get("promoted_count") or 0) > 0


def _lane_decision(
    gate: dict[str, Any],
    promo: dict[str, Any],
    *,
    lane_label: str,
) -> dict[str, Any]:
    pending = bool(gate.get("gate_pass")) or _promotion_pending(promo)
    if pending:
        return {
            "lane": lane_label,
            "promote_to_pending": True,
            "canonical_merge": False,
            "human_decision": f"{lane_label.upper()}_PROMOTED_TO_PENDING",
            "promoted_count": int(promo.get("promoted_count") or gate.get("survivor_count") or 0),
        }
    return {
        "lane": lane_label,
        "promote_to_pending": False,
        "canonical_merge": False,
        "human_decision": f"HOLD_{lane_label.upper()}",
        "promoted_count": 0,
    }


def _combined_decision(ann: dict[str, Any], d4: dict[str, Any]) -> dict[str, Any]:
    ann_ok = ann.get("promote_to_pending")
    d4_ok = d4.get("promote_to_pending")
    if ann_ok and d4_ok:
        verdict = "BOTH_LANES_PROMOTED_TO_PENDING"
        reason = (
            f"ANN-lite {ann.get('promoted_count')}건 + offline_4d {d4.get('promoted_count')}건 pending JSONL. "
            "canonical merge는 lane별 --acknowledge-canonical-risk 별도."
        )
    elif ann_ok:
        verdict = "ANN_LITE_PROMOTED_TO_PENDING"
        reason = "ANN-lite pending 완료. offline_4d는 gate/signoff 확인."
    elif d4_ok:
        verdict = "OFFLINE_4D_PROMOTED_TO_PENDING"
        reason = "offline_4d pending 완료. ANN-lite는 gate/signoff 확인."
    else:
        verdict = "HOLD_REVIEW_ANN_LITE_FIRST"
        reason = "signoff/gate 미충족 — queue review_decision 후 lane signoff 갱신 필요."
    return {
        "promote_to_pending": bool(ann_ok or d4_ok),
        "canonical_merge": False,
        "auto_promote": bool(ann_ok or d4_ok),
        "human_decision": verdict,
        "reason_ko": reason,
        "lanes": {"ann_lite": ann, "offline_4d_knn": d4},
    }


def _gate_summary(gate: dict[str, Any]) -> dict[str, Any]:
    return {
        "lane_id": gate.get("lane_id"),
        "status": gate.get("status"),
        "gate_pass": bool(gate.get("gate_pass")),
        "survivor_count": gate.get("survivor_count"),
        "checks": gate.get("checks"),
        "recommended_next": gate.get("recommended_next"),
    }


def _item_row(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "queue_rank": item.get("queue_rank"),
        "lane_id": item.get("lane_id"),
        "priority": item.get("priority"),
        "pair_key": item.get("pair_key"),
        "similarity": item.get("similarity"),
        "review_status": item.get("review_status"),
    }


def _render_md(payload: dict[str, Any]) -> str:
    stats = payload.get("queue_stats") or {}
    gates = payload.get("gates") or {}
    decision = payload.get("decision") or {}
    graph = payload.get("canonical_graph") or {}
    lines = [
        "# Logos candidate edges — Human review pack (research_only · NON_GATING)",
        "",
        f"- generated: `{payload.get('generated_at_utc')}`",
        f"- recommendation: **{payload.get('recommendation', 'ann_lite_primary')}**",
        "",
        "## Canonical graph (read-only baseline)",
        "",
        f"- nodes: `{graph.get('nodes_line_count', 'n/a')}`",
        f"- edges: `{graph.get('edges_line_count', 'n/a')}`",
        "",
        "## Queue stats",
        "",
        f"| Metric | Count |",
        f"|--------|------:|",
        f"| total_items | {stats.get('total_items', 'n/a')} |",
        f"| ann_lite primary | {stats.get('ann_lite_primary', 'n/a')} |",
        f"| offline_4d only | {stats.get('offline_4d_only', 'n/a')} |",
        f"| pending | {stats.get('pending_count', 'n/a')} |",
        "",
        "## Promotion gates",
        "",
        f"- **ann_lite:** `{gates.get('ann_lite', {}).get('status')}` "
        f"(pass={gates.get('ann_lite', {}).get('gate_pass')}, "
        f"survivors={gates.get('ann_lite', {}).get('survivor_count')})",
        f"- **offline_4d_knn:** `{gates.get('offline_4d_knn', {}).get('status')}` "
        f"(pass={gates.get('offline_4d_knn', {}).get('gate_pass')}, "
        f"survivors={gates.get('offline_4d_knn', {}).get('survivor_count')})",
        "",
        "## Decision (human — not auto-applied)",
        "",
        f"- **promote_to_pending:** `{decision.get('promote_to_pending')}`",
        f"- **canonical_merge:** `{decision.get('canonical_merge')}`",
        f"- **verdict:** `{decision.get('human_decision')}`",
        f"- {decision.get('reason_ko', '')}",
        "",
        "## ANN-lite primary (review first)",
        "",
        "| rank | pair | similarity |",
        "|-----:|------|----------:|",
    ]
    for row in payload.get("ann_lite_primary_items") or []:
        lines.append(
            f"| {row.get('queue_rank')} | `{row.get('pair_key')}` | {row.get('similarity')} |"
        )
    lines.extend(
        [
            "",
            f"## offline_4d_knn sample (top {SECONDARY_4D_SAMPLE} of secondary lane)",
            "",
            "| rank | pair | similarity |",
            "|-----:|------|----------:|",
        ]
    )
    for row in payload.get("offline_4d_sample_items") or []:
        lines.append(
            f"| {row.get('queue_rank')} | `{row.get('pair_key')}` | {row.get('similarity')} |"
        )
    lines.extend(
        [
            "",
            "## Sign-off checklist",
            "",
            "1. Review ANN-lite 45 rows in queue JSON — set `review_decision`: approve | reject | defer",
            "2. Update lane signoff JSON (`approved=true`, approver, `approved_at_utc`)",
            "3. Re-run `check_logos_candidate_edge_promotion_gate_v1.py --lane-id ann_lite`",
            "4. On gate PASS: `promote_logos_candidate_edge_survivors_v1.py --lane-id ann_lite`",
            "5. 4D lane: requires `saturation_warning_acknowledged=true` on signoff before promote",
            "",
            f"Queue: `{payload.get('inputs', {}).get('queue_json')}`",
            "",
            f"Rerun: `py scripts/build_logos_candidate_edge_human_review_pack_v1.py`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--queue-json", type=Path, default=DEFAULT_QUEUE)
    ap.add_argument("--gate-ann-json", type=Path, default=DEFAULT_GATE_ANN)
    ap.add_argument("--gate-4d-json", type=Path, default=DEFAULT_GATE_4D)
    ap.add_argument("--graph-bundle-json", type=Path, default=DEFAULT_GRAPH)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT_MD)
    ap.add_argument("--skip-md", action="store_true")
    args = ap.parse_args(argv)

    queue_path = args.queue_json if args.queue_json.is_absolute() else ROOT / args.queue_json
    if not queue_path.is_file():
        print(f"Missing queue: {queue_path}", file=__import__("sys").stderr)
        return 2

    queue = _load(queue_path)
    gate_ann = _load(args.gate_ann_json if args.gate_ann_json.is_absolute() else ROOT / args.gate_ann_json)
    gate_4d = _load(args.gate_4d_json if args.gate_4d_json.is_absolute() else ROOT / args.gate_4d_json)
    promo_ann = _load(DEFAULT_PROMO_ANN)
    promo_4d = _load(DEFAULT_PROMO_4D)
    graph = _load(args.graph_bundle_json if args.graph_bundle_json.is_absolute() else ROOT / args.graph_bundle_json)

    items = list(queue.get("items") or [])
    ann_primary = [_item_row(i) for i in items if i.get("lane_id") == "ann_lite" and i.get("priority") == "primary"]
    d4_secondary = [_item_row(i) for i in items if i.get("lane_id") == "offline_4d_knn"][:SECONDARY_4D_SAMPLE]

    graph_files = graph.get("graph_files") if isinstance(graph.get("graph_files"), dict) else {}
    ann_lane = _lane_decision(gate_ann, promo_ann, lane_label="ann_lite")
    d4_lane = _lane_decision(gate_4d, promo_4d, lane_label="offline_4d_knn")
    decision = _combined_decision(ann_lane, d4_lane)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "recommendation": queue.get("recommendation") or "ann_lite_primary",
        "queue_stats": queue.get("stats"),
        "gates": {
            "ann_lite": _gate_summary(gate_ann),
            "offline_4d_knn": _gate_summary(gate_4d),
        },
        "canonical_graph": {
            "nodes_line_count": graph_files.get("nodes_line_count"),
            "edges_line_count": graph_files.get("edges_line_count"),
            "bundle_path": _rel(args.graph_bundle_json if args.graph_bundle_json.is_absolute() else ROOT / args.graph_bundle_json),
        },
        "ann_lite_primary_items": ann_primary,
        "offline_4d_sample_items": d4_secondary,
        "decision": decision,
        "signoff_paths": {
            "ann_lite_fixture": "docs/final/fixtures/logos_candidate_edge_promotion_signoff_ann_lite_v1.example.json",
            "ann_lite_operational": "docs/final/artifacts/logos_candidate_edge_promotion_signoff_ann_lite_v1_latest.json",
            "offline_4d_fixture": "docs/final/fixtures/logos_candidate_edge_promotion_signoff_v1.example.json",
        },
        "pending_paths": {
            "ann_lite": "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_ann_lite_v1.jsonl",
            "offline_4d_knn": "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_v1.jsonl",
        },
        "inputs": {
            "queue_json": _rel(queue_path),
            "gate_ann_json": _rel(args.gate_ann_json if args.gate_ann_json.is_absolute() else ROOT / args.gate_ann_json),
            "gate_4d_json": _rel(args.gate_4d_json if args.gate_4d_json.is_absolute() else ROOT / args.gate_4d_json),
        },
    }

    out_json = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out_md = args.out_md if args.out_md.is_absolute() else ROOT / args.out_md
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if not args.skip_md:
        out_md.write_text(_render_md(payload), encoding="utf-8")

    print(str(out_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
