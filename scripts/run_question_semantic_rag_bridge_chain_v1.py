#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Question → Logos subgraph router → semantic bundle → magic_orb insight + graph_bloom."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable

DEFAULT_OUT_CHAIN = ROOT / "reports/question_semantic_rag_bridge_chain_v1_latest.json"
DEFAULT_ROUTER_OUT = ROOT / "reports/question_logos_subgraph_router_sidecar_v1_latest.json"
DEFAULT_INSIGHT_OUT = ROOT / "docs/final/artifacts/magic_orb_question_insight_v1_latest.json"
DEFAULT_SHADOW = ROOT / "docs/final/artifacts/research_shadow_lane_hypothesis_tree_v1_latest.json"
DEFAULT_DIGEST = ROOT / "docs/final/artifacts/comparative_theology_panorama_digest_v1_latest.json"
BY_QUERY_REPORTS = ROOT / "reports/magic_orb_insight_by_query"
BY_QUERY_PUBLIC = ROOT / "projects/mkm/mkm-life/public/data/magic_orb_insight_by_query"

JOB_QUERY_IDS = frozenset({"job_suffering_reason", "job_prologue_suffering"})
JOB_QUERY_RE = re.compile(r"욥|job", re.I)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _query_hash16(query: str) -> str:
    norm = " ".join(query.strip().split())[:800]
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()[:16]


def _sync_by_query_artifacts(query: str, query_id: str, insight_path: Path) -> dict[str, Any]:
    BY_QUERY_REPORTS.mkdir(parents=True, exist_ok=True)
    BY_QUERY_PUBLIC.mkdir(parents=True, exist_ok=True)
    text = insight_path.read_text(encoding="utf-8")
    report_copy = BY_QUERY_REPORTS / f"insight_{query_id}_latest.json"
    report_copy.write_text(text, encoding="utf-8")
    qh = _query_hash16(query)
    pub_copy = BY_QUERY_PUBLIC / f"{qh}.json"
    pub_copy.write_text(text, encoding="utf-8")
    return {
        "ok": True,
        "query_key_hash": qh,
        "public": str(pub_copy.relative_to(ROOT)).replace("\\", "/"),
        "report": str(report_copy.relative_to(ROOT)).replace("\\", "/"),
    }


def _run(cmd: list[str]) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.call(cmd, cwd=str(ROOT))


def _is_job_context(query: str, query_id: str) -> bool:
    if query_id in JOB_QUERY_IDS:
        return True
    return bool(JOB_QUERY_RE.search(query))


def _run_panorama_preflight(*, query_id: str, skip_panorama: bool, dry_run: bool) -> dict[str, Any]:
    """Shadow boundary + comparative digest for job / 욥 queries."""
    if skip_panorama:
        return {"ok": True, "skipped": True}

    steps: dict[str, Any] = {}
    shadow_cmd = [
        PY,
        str(ROOT / "scripts/build_research_shadow_lane_hypothesis_tree_v1.py"),
        "--query-id",
        query_id,
    ]
    digest_cmd = [PY, str(ROOT / "scripts/build_comparative_theology_panorama_digest_v1.py")]

    if dry_run:
        print("[dry-run]", " ".join(shadow_cmd))
        print("[dry-run]", " ".join(digest_cmd))
        return {"ok": True, "dry_run": True}

    rc = _run(shadow_cmd)
    steps["shadow_lane_tree"] = {"ok": rc == 0, "exit_code": rc}
    if rc != 0:
        return {"ok": False, "steps": steps}

    rc = _run(digest_cmd)
    steps["comparative_digest"] = {"ok": rc == 0, "exit_code": rc}
    if rc != 0:
        return {"ok": False, "steps": steps}

    return {"ok": True, "steps": steps}


def main() -> int:
    ap = argparse.ArgumentParser(description="Run question semantic RAG bridge chain.")
    ap.add_argument("--query", default="")
    ap.add_argument("--query-file", type=Path, default=None, help="UTF-8 file with query text (PS encoding safe)")
    ap.add_argument("--query-id", default="q01")
    ap.add_argument("--top-bridges", type=int, default=6)
    ap.add_argument("--skip-ann-lite", action="store_true")
    ap.add_argument("--skip-panorama", action="store_true", help="skip shadow+digest preflight")
    ap.add_argument("--expand-graph", action="store_true", help="enrich graph_bloom from bible_meaning_graph")
    ap.add_argument(
        "--include-4d-shadow",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="attach 4D path coherence shadow + rerank router paths",
    )
    ap.add_argument("--sync-public", action="store_true")
    ap.add_argument(
        "--sync-public-by-query",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="copy insight to magic_orb_insight_by_query/{hash}.json (job queries)",
    )
    ap.add_argument("--router-out", type=Path, default=DEFAULT_ROUTER_OUT)
    ap.add_argument("--insight-out", type=Path, default=DEFAULT_INSIGHT_OUT)
    ap.add_argument("--bloom-out", type=Path, default=ROOT / "docs/final/artifacts/magic_orb_graph_bloom_v1_latest.json")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT_CHAIN)
    ap.add_argument(
        "--with-post-llm-fill",
        action="store_true",
        help="template_expand post-LLM fill on imagination_path/unknown_gap after gate",
    )
    ap.add_argument(
        "--post-llm-fill-live",
        action="store_true",
        help="tier_15 live fill (requires MKM_FOUR_SLOT_LLM_FILL_ALLOWED=1)",
    )
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--record-ledger",
        action="store_true",
        help="append logos_query_path_ledger_v1 row from router sidecar (B-track)",
    )
    args = ap.parse_args()

    query = str(args.query or "").strip()
    if args.query_file:
        qpath = args.query_file if args.query_file.is_absolute() else ROOT / args.query_file
        query = qpath.read_text(encoding="utf-8-sig").strip()
    if not query:
        ap.error("provide --query or --query-file")

    router_out = args.router_out if args.router_out.is_absolute() else ROOT / args.router_out
    chain_out = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    insight_out = args.insight_out if args.insight_out.is_absolute() else ROOT / args.insight_out
    bloom_out = args.bloom_out if args.bloom_out.is_absolute() else ROOT / args.bloom_out

    steps: dict[str, Any] = {}

    router_cmd = [
        PY,
        str(ROOT / "scripts/run_logos_subgraph_graphrag_router_v1.py"),
        "--query-id",
        args.query_id,
        "--query",
        query,
        "--top-bridges",
        str(args.top_bridges),
        "--output-json",
        str(router_out.relative_to(ROOT)).replace("\\", "/"),
    ]
    if args.dry_run:
        print("[dry-run]", " ".join(router_cmd))
        steps["subgraph_router"] = {"ok": True, "dry_run": True}
    else:
        rc = _run(router_cmd)
        steps["subgraph_router"] = {"ok": rc == 0, "exit_code": rc, "artifact": str(router_out)}
        if rc != 0:
            return rc

    if not args.dry_run and args.include_4d_shadow and router_out.is_file():
        shadow_cmd = [
            PY,
            str(ROOT / "scripts/logos_question_4d_shadow_v1.py"),
            "--router-json",
            str(router_out.relative_to(ROOT)).replace("\\", "/"),
        ]
        rc = _run(shadow_cmd)
        steps["four_d_shadow"] = {"ok": rc == 0, "exit_code": rc, "artifact": str(router_out)}
        if rc != 0:
            return rc
        gate_cmd = [
            PY,
            str(ROOT / "scripts/check_logos_question_4d_coherence_gate_v1.py"),
            "--router-json",
            str(router_out.relative_to(ROOT)).replace("\\", "/"),
        ]
        gate_rc = _run(gate_cmd)
        steps["four_d_coherence_gate"] = {"ok": gate_rc == 0, "exit_code": gate_rc}
    elif args.dry_run and args.include_4d_shadow:
        steps["four_d_shadow"] = {"ok": True, "dry_run": True}

    if _is_job_context(query, args.query_id):
        pano = _run_panorama_preflight(
            query_id=args.query_id,
            skip_panorama=args.skip_panorama,
            dry_run=args.dry_run,
        )
        steps["panorama_preflight"] = pano
        if not pano.get("ok"):
            return 1

    bundle_path = ROOT / "docs/final/artifacts/semantic_rag_bridge_insight_bundle_v1_latest.json"
    if bundle_path.is_file():
        steps["bridge_bundle"] = {
            "ok": True,
            "artifact": str(bundle_path.relative_to(ROOT)).replace("\\", "/"),
            "reused": True,
        }
    else:
        steps["bridge_bundle"] = {
            "ok": True,
            "artifact": None,
            "reused": False,
            "note": "bundle missing; insight builder synthesizes rag from router",
        }

    ann_status = "skipped_flag"
    if not args.skip_ann_lite:
        ann_status = "skipped_flag"
    steps["ann_lite"] = {"status": ann_status}

    bloom_cmd = [
        PY,
        str(ROOT / "scripts/build_magic_orb_graph_bloom_v1.py"),
        "--query",
        query,
        "--router-json",
        str(router_out),
    ]
    if args.expand_graph:
        bloom_cmd.append("--expand-graph")

    bloom_cmd.extend(["--out-json", str(bloom_out)])

    if args.dry_run:
        print("[dry-run]", " ".join(bloom_cmd))
    else:
        rc = _run(bloom_cmd)
        if rc != 0:
            return rc

    insight_cmd = [
        PY,
        str(ROOT / "scripts/build_magic_orb_question_insight_payload_v1.py"),
        "--query",
        query,
        "--query-id",
        args.query_id,
        "--router-json",
        str(router_out),
        "--bloom-json",
        str(bloom_out),
        "--out-json",
        str(insight_out),
        "--shadow-json",
        str(DEFAULT_SHADOW),
        "--digest-json",
        str(DEFAULT_DIGEST),
        "--caps-json-inline",
        json.dumps(
            {
                "rag_evidence": 24,
                "subgraph_paths": 12,
                "subgraph_verses": 12,
                "ann_top_k_default": 8,
                "lod_node_cap": 48,
                "lod_edge_cap": 56,
            }
        ),
    ]
    if args.sync_public:
        insight_cmd.append("--sync-public")

    if args.dry_run:
        print("[dry-run]", " ".join(insight_cmd))
        steps["insight_payload"] = {"ok": True, "dry_run": True}
    else:
        rc = _run(insight_cmd)
        steps["insight_payload"] = {"ok": rc == 0, "exit_code": rc, "artifact": str(insight_out)}
        if rc != 0:
            return rc

        validate_cmd = [
            PY,
            str(ROOT / "scripts/validate_magic_orb_four_slot_v1.py"),
            "--insight-json",
            str(insight_out),
        ]
        if not _is_job_context(query, args.query_id):
            validate_cmd.append("--allow-missing-four-slot")
        vrc = _run(validate_cmd)
        steps["four_slot_validate"] = {"ok": vrc == 0, "exit_code": vrc}
        if vrc != 0:
            return vrc

        post_llm_cmd = [
            PY,
            str(ROOT / "scripts/run_magic_orb_four_slot_post_llm_gate_v1.py"),
            "--insight-json",
            str(insight_out),
        ]
        if not _is_job_context(query, args.query_id):
            post_llm_cmd.append("--allow-missing-four-slot")
        plrc = _run(post_llm_cmd)
        steps["four_slot_post_llm_gate"] = {"ok": plrc == 0, "exit_code": plrc}
        if plrc != 0:
            return plrc

        if args.with_post_llm_fill:
            fill_cmd = [
                PY,
                str(ROOT / "scripts/run_magic_orb_four_slot_post_llm_fill_chain_v1.py"),
                "--insight-json",
                str(insight_out),
                "--human-gate-ack",
            ]
            if args.post_llm_fill_live:
                fill_cmd.extend(["--mode", "live", "--enable-tier15-envelope", "--rebuild-envelope"])
            else:
                fill_cmd.extend(["--mode", "template_expand"])
            frc = _run(fill_cmd)
            steps["post_llm_fill_chain"] = {"ok": frc == 0, "exit_code": frc}
            if frc != 0:
                return frc

        if args.sync_public_by_query and _is_job_context(query, args.query_id):
            byq = _sync_by_query_artifacts(query, args.query_id, insight_out)
            steps["sync_public_by_query"] = byq
        else:
            steps["sync_public_by_query"] = {"ok": True, "skipped": True}

    router_doc = json.loads(router_out.read_text(encoding="utf-8-sig")) if router_out.is_file() else {}
    chain_doc = {
        "schema": "question_semantic_rag_bridge_chain_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "query": query,
        "query_id": args.query_id,
        "steps": {
            **steps,
            "subgraph_router": {
                "ok": True,
                "artifact": str(router_out.relative_to(ROOT)).replace("\\", "/"),
                "bridges_matched": router_doc.get("bridges_matched"),
                "paths": len(router_doc.get("paths") or []),
                "verse_ids": len(router_doc.get("verse_ids") or []),
            },
            "ann_lite": steps.get("ann_lite", {"status": ann_status}),
            "bridge_bundle": steps.get("bridge_bundle", {"ok": True}),
            "graph_bloom": {
                "ok": True,
                "artifact": str(bloom_out.relative_to(ROOT)).replace("\\", "/"),
                "expand_graph": bool(args.expand_graph),
            },
            "insight_payload": steps.get("insight_payload", {"ok": True}),
            "four_slot_validate": steps.get("four_slot_validate", {"ok": True, "skipped": args.dry_run}),
        },
        "caps": {
            "rag_evidence": 24,
            "subgraph_paths": 12,
            "subgraph_verses": 12,
            "ann_top_k_default": 8,
            "lod_node_cap": 48,
            "lod_edge_cap": 56,
        },
        "policy": {
            "track": "B-track",
            "gating": "NON_GATING",
            "hypothesis_label": "[HYPO]",
            "must_not_merge_with": [
                "track_a_compression",
                "global_atom_network_pilot",
                "live_trading_trigger",
                "prophecy_hit_rate",
            ],
        },
        "generator": "run_question_semantic_rag_bridge_chain_v1.py@1.2.0",
    }
    chain_out.parent.mkdir(parents=True, exist_ok=True)
    chain_out.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.record_ledger and not args.dry_run and router_out.is_file():
        from scripts.logos_query_path_ledger_v1 import (
            append_logos_query_path_ledger_line,
            build_entry_from_router,
        )

        router_for_ledger = json.loads(router_out.read_text(encoding="utf-8-sig"))
        ledger_entry = build_entry_from_router(
            router_for_ledger,
            query_id=args.query_id,
            chain_path=chain_out,
            insight_path=insight_out if insight_out.is_file() else None,
            router_path=router_out,
        )
        ledger_daily = append_logos_query_path_ledger_line(ROOT, ledger_entry)
        chain_doc["steps"]["path_ledger"] = {
            "ok": True,
            "ledger_id": ledger_entry["ledger_id"],
            "selected_path_id": ledger_entry["retrieval"]["selected_path_id"],
            "daily": str(ledger_daily.relative_to(ROOT)).replace("\\", "/"),
            "latest": "reports/logos_query_path_ledger_v1_latest.jsonl",
        }
        chain_out.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "chain": str(chain_out), "insight": str(insight_out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
