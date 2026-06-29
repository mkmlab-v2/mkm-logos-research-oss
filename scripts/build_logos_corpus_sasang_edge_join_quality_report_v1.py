#!/usr/bin/env python3
"""Build edge join quality report for 31k sasang+logos graph bundle (B-track)."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GRAPH_BUNDLE = ROOT / "docs/final/artifacts/logos_corpus_sasang_routing_graph_bundle_v1_latest.json"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_JSONL = ROOT / "docs/final/artifacts/sasang_routing_sidecar_corpus_31k_v1.jsonl"
DEFAULT_OUT = ROOT / "reports/logos_corpus_sasang_edge_join_quality_v1_latest.json"

VERSE_REF_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*\.\d+\.\d+$")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _iter_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        try:
            row = json.loads(s)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _edge_side_ref(row: dict[str, Any], *, side: str) -> str | None:
    ref_keys = ["source_ref", "src_ref"] if side == "src" else ["target_ref", "dst_ref"]
    node_keys = ["src_node_id", "src_node", "source_node_id"] if side == "src" else ["dst_node_id", "dst_node", "target_node_id"]
    for key in ref_keys:
        val = row.get(key)
        if isinstance(val, str) and VERSE_REF_RE.match(val.strip()):
            return val.strip()
    for key in node_keys:
        val = row.get(key)
        if isinstance(val, str) and "::" in val:
            tail = val.split("::", 1)[1].strip()
            if VERSE_REF_RE.match(tail):
                return tail
    return None


def build_report(*, graph_bundle_path: Path, edges_path: Path, corpus_jsonl_path: Path) -> dict[str, Any]:
    graph_bundle = _load_json(graph_bundle_path) if graph_bundle_path.is_file() else {}
    corpus_rows = _iter_jsonl(corpus_jsonl_path) if corpus_jsonl_path.is_file() else []
    corpus_ids = {str(r.get("verse_id") or "") for r in corpus_rows if r.get("verse_id")}

    per_type: dict[str, dict[str, int]] = defaultdict(
        lambda: {
            "total": 0,
            "touching_corpus": 0,
            "both_parsed_refs": 0,
            "any_parsed_refs": 0,
            "src_parsed_refs": 0,
            "dst_parsed_refs": 0,
            "single_side_parsed_refs": 0,
        }
    )
    malformed = 0
    parsed_src = 0
    parsed_dst = 0
    touching = 0
    edge_types = Counter[str]()

    if edges_path.is_file():
        for row in _iter_jsonl(edges_path):
            edge_type = str(row.get("edge_type") or "unknown")
            edge_types[edge_type] += 1
            per_type[edge_type]["total"] += 1

            src = _edge_side_ref(row, side="src")
            dst = _edge_side_ref(row, side="dst")
            if src:
                parsed_src += 1
                per_type[edge_type]["src_parsed_refs"] += 1
            if dst:
                parsed_dst += 1
                per_type[edge_type]["dst_parsed_refs"] += 1
            if src or dst:
                per_type[edge_type]["any_parsed_refs"] += 1
            if src and dst:
                per_type[edge_type]["both_parsed_refs"] += 1
            elif src or dst:
                per_type[edge_type]["single_side_parsed_refs"] += 1
            if not src and not dst:
                malformed += 1

            if (src and src in corpus_ids) or (dst and dst in corpus_ids):
                touching += 1
                per_type[edge_type]["touching_corpus"] += 1

    per_type_rows: list[dict[str, Any]] = []
    for et in sorted(per_type.keys()):
        row = per_type[et]
        total = row["total"]
        row["touch_ratio"] = round((row["touching_corpus"] / total), 6) if total else 0.0
        row["parse_ratio"] = round((row["both_parsed_refs"] / total), 6) if total else 0.0
        row["any_parse_ratio"] = round((row["any_parsed_refs"] / total), 6) if total else 0.0
        row["single_side_parse_ratio"] = round((row["single_side_parsed_refs"] / total), 6) if total else 0.0
        row["src_parse_ratio"] = round((row["src_parsed_refs"] / total), 6) if total else 0.0
        row["dst_parse_ratio"] = round((row["dst_parsed_refs"] / total), 6) if total else 0.0
        row["edge_type"] = et
        per_type_rows.append(dict(row))

    total_edges = sum(v["total"] for v in per_type.values())
    return {
        "schema": "logos_corpus_sasang_edge_join_quality_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "track_a_blocked": True,
        "graph_bundle_path": str(graph_bundle_path.relative_to(ROOT)).replace("\\", "/") if graph_bundle_path.is_file() else str(graph_bundle_path),
        "corpus_jsonl_path": str(corpus_jsonl_path.relative_to(ROOT)).replace("\\", "/") if corpus_jsonl_path.is_file() else str(corpus_jsonl_path),
        "summary": {
            "corpus_verse_count": len(corpus_ids),
            "edge_total": total_edges,
            "edges_touching_corpus": touching,
            "edge_touch_ratio": round((touching / total_edges), 6) if total_edges else 0.0,
            "parsed_src_count": parsed_src,
            "parsed_dst_count": parsed_dst,
            "parsed_any_count": sum(v["any_parsed_refs"] for v in per_type.values()),
            "parsed_both_count": sum(v["both_parsed_refs"] for v in per_type.values()),
            "parsed_single_side_count": sum(v["single_side_parsed_refs"] for v in per_type.values()),
            "malformed_no_ref_count": malformed,
            "graph_bundle_edges_touching_corpus": ((graph_bundle.get("graph_overlap") or {}).get("meaning_graph_edges_touching_corpus")),
        },
        "edge_type_quality": per_type_rows,
        "top_edge_types": dict(edge_types.most_common(15)),
        "disclaimer_ko": "조인 품질 리포트는 B-track 관측 전용. Track A·예언·실매매 트리거가 아니다.",
        "reproduce": "py scripts/build_logos_corpus_sasang_edge_join_quality_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--graph-bundle", type=Path, default=DEFAULT_GRAPH_BUNDLE)
    ap.add_argument("--edges", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--corpus-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.edges.is_file():
        print(json.dumps({"ok": False, "error": f"missing edges jsonl: {args.edges}"}))
        return 1
    if not args.corpus_jsonl.is_file():
        print(json.dumps({"ok": False, "error": f"missing corpus jsonl: {args.corpus_jsonl}"}))
        return 1

    doc = build_report(
        graph_bundle_path=args.graph_bundle,
        edges_path=args.edges,
        corpus_jsonl_path=args.corpus_jsonl,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "edge_total": doc["summary"]["edge_total"], "touch_ratio": doc["summary"]["edge_touch_ratio"], "out": str(args.out)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
