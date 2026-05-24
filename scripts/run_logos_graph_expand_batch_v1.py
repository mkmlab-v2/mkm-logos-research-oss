#!/usr/bin/env python3
"""DF-P2-04: Append verse nodes to meaning graph in bounded batches ([HYPO] B-track)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_CANON = ROOT / "data/logos/verse_decoded_v2.jsonl"
DEFAULT_CANDIDATES = ROOT / "docs/final/artifacts/bible_meaning_insight_candidates_latest.json"
DEFAULT_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_graph_bundle_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_graph_expand_batch_v1_latest.json"
BUNDLE_SCRIPT = ROOT / "scripts/build_logos_corpus_graph_bundle_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            n += 1
    return n


def _load_node_ids(path: Path) -> set[str]:
    ids: set[str] = set()
    if not path.is_file():
        return ids
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        nid = row.get("node_id")
        if nid:
            ids.add(str(nid))
    return ids


def _pick_hub_seed(candidates_path: Path) -> str:
    if candidates_path.is_file():
        doc = json.loads(candidates_path.read_text(encoding="utf-8-sig"))
        cands = list(doc.get("candidates") or [])
        cands.sort(key=lambda c: float(c.get("hub_score") or 0), reverse=True)
        if cands:
            return str(cands[0].get("source_node_id") or "aramaic::Dan.2.10")
    return "aramaic::Dan.2.10"


def _missing_edge_endpoints(nodes_path: Path, edges_path: Path) -> list[str]:
    node_ids = _load_node_ids(nodes_path)
    missing: list[str] = []
    seen: set[str] = set()
    if not edges_path.is_file():
        return missing
    for line in edges_path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        for key in ("src_node_id", "dst_node_id"):
            nid = str(row.get(key) or "")
            if not nid or nid in node_ids or nid in seen:
                continue
            seen.add(nid)
            missing.append(nid)
    return missing


def _stub_node(node_id: str, ref: str) -> dict[str, Any]:
    return {
        "schema": "aramaic_graph_node_v1",
        "node_id": node_id,
        "corpus": "aramaic",
        "ref": ref,
        "text_norm": "",
        "time_bucket": "canon_expand_batch",
        "theme_tags": ["canon_expand"],
        "regime_tags": [],
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "source": "df_p2_04_graph_expand_batch",
    }


def _stub_edge(src: str, dst: str) -> dict[str, Any]:
    return {
        "schema": "bible_meaning_graph_edge_v1",
        "src_node_id": src,
        "dst_node_id": dst,
        "edge_type": "theme_association",
        "weight": 0.55,
        "source": "df_p2_04_graph_expand_batch",
    }


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def _expand_from_corpus(
    canon_path: Path,
    node_ids: set[str],
    hub_seed: str,
    batch_size: int,
    max_scan_rows: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], int]:
    nodes_out: list[dict[str, Any]] = []
    edges_out: list[dict[str, Any]] = []
    scanned = 0
    with canon_path.open(encoding="utf-8") as fh:
        for line in fh:
            if len(nodes_out) >= batch_size:
                break
            if max_scan_rows > 0 and scanned >= max_scan_rows:
                break
            s = line.strip()
            if not s:
                continue
            scanned += 1
            row = json.loads(s)
            vid = str(row.get("verse_id") or "").strip()
            if not vid:
                continue
            nid = f"aramaic::{vid}"
            if nid in node_ids:
                continue
            node_ids.add(nid)
            nodes_out.append(_stub_node(nid, vid))
            edges_out.append(_stub_edge(nid, hub_seed))
    return nodes_out, edges_out, scanned


def main() -> int:
    ap = argparse.ArgumentParser(description="DF-P2-04 graph expand batch (+N nodes, monotonic).")
    ap.add_argument("--nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--canon-jsonl", type=Path, default=DEFAULT_CANON)
    ap.add_argument("--candidates-json", type=Path, default=DEFAULT_CANDIDATES)
    ap.add_argument("--batch-size", type=int, default=500)
    ap.add_argument("--max-scan-rows", type=int, default=0, help="0 = scan until batch filled")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-bundle-refresh", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    nodes_path = args.nodes_jsonl if args.nodes_jsonl.is_absolute() else ROOT / args.nodes_jsonl
    edges_path = args.edges_jsonl if args.edges_jsonl.is_absolute() else ROOT / args.edges_jsonl
    canon_path = args.canon_jsonl if args.canon_jsonl.is_absolute() else ROOT / args.canon_jsonl
    candidates_path = args.candidates_json if args.candidates_json.is_absolute() else ROOT / args.candidates_json
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json

    if not canon_path.is_file():
        print(f"error: canon jsonl not found: {canon_path}", file=sys.stderr)
        return 2

    before_nodes = _count_lines(nodes_path)
    before_edges = _count_lines(edges_path)
    hub_seed = _pick_hub_seed(candidates_path)
    node_ids = _load_node_ids(nodes_path)
    batch_size = max(0, int(args.batch_size))

    missing_eps = _missing_edge_endpoints(nodes_path, edges_path)
    repair_nodes: list[dict[str, Any]] = []
    repair_edges: list[dict[str, Any]] = []
    for nid in missing_eps:
        if len(repair_nodes) >= batch_size:
            break
        ref = nid.split("::", 1)[-1] if "::" in nid else nid
        repair_nodes.append(_stub_node(nid, ref))
        repair_edges.append(_stub_edge(nid, hub_seed))
        node_ids.add(nid)

    remaining = max(0, batch_size - len(repair_nodes))
    corpus_nodes: list[dict[str, Any]] = []
    corpus_edges: list[dict[str, Any]] = []
    scanned = 0
    if remaining > 0:
        corpus_nodes, corpus_edges, scanned = _expand_from_corpus(
            canon_path,
            node_ids,
            hub_seed,
            remaining,
            int(args.max_scan_rows),
        )

    new_nodes = repair_nodes + corpus_nodes
    new_edges = repair_edges + corpus_edges

    if args.dry_run:
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "before_nodes": before_nodes,
                    "planned_nodes": len(new_nodes),
                    "hub_seed": hub_seed,
                },
                ensure_ascii=False,
            )
        )
        return 0

    appended_nodes = _append_jsonl(nodes_path, new_nodes)
    appended_edges = _append_jsonl(edges_path, new_edges)
    after_nodes = _count_lines(nodes_path)
    after_edges = _count_lines(edges_path)

    if after_nodes < before_nodes:
        print("error: nodes_line_count decreased", file=sys.stderr)
        return 2

    bundle_path = DEFAULT_BUNDLE
    bundle_exit = 0
    if not args.skip_bundle_refresh and BUNDLE_SCRIPT.is_file():
        proc = subprocess.run([sys.executable, str(BUNDLE_SCRIPT)], cwd=str(ROOT))
        bundle_exit = int(proc.returncode)
        if bundle_path.is_file():
            bundle_path = bundle_path.resolve()

    bundle_nodes = None
    if bundle_path.is_file():
        bundle_doc = json.loads(bundle_path.read_text(encoding="utf-8-sig"))
        bundle_nodes = (bundle_doc.get("graph_files") or {}).get("nodes_line_count")

    report = {
        "schema": "logos_graph_expand_batch_v1",
        "df_mission_id": "DF-P2-04",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": {"non_gating": True, "no_trade_signals": True},
        "hub_seed_node_id": hub_seed,
        "batch_size_target": batch_size,
        "counts": {
            "nodes_before": before_nodes,
            "nodes_after": after_nodes,
            "nodes_appended": appended_nodes,
            "edges_before": before_edges,
            "edges_after": after_edges,
            "edges_appended": appended_edges,
            "endpoint_repair_nodes": len(repair_nodes),
            "corpus_expand_nodes": len(corpus_nodes),
            "canon_rows_scanned": scanned,
        },
        "monotonic": {
            "nodes_line_count_ok": after_nodes >= before_nodes,
            "bundle_nodes_line_count": bundle_nodes,
        },
        "roadmap": {"target_nodes": 3000, "note": "B-track batch expand; not Track A / live trading."},
        "paths": {
            "nodes_jsonl": str(nodes_path.resolve()).replace("\\", "/"),
            "edges_jsonl": str(edges_path.resolve()).replace("\\", "/"),
            "bundle_json": str(bundle_path).replace("\\", "/") if bundle_path else None,
        },
        "bundle_refresh_exit_code": bundle_exit,
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0 if bundle_exit == 0 else bundle_exit


if __name__ == "__main__":
    raise SystemExit(main())
