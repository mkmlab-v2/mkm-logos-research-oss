#!/usr/bin/env python3
"""Append approved pending candidate edges to canonical graph JSONL (deduped).

Requires prior promotion gate PASS + pending JSONL. Does not auto-run without
--acknowledge-canonical-risk.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

from logos_candidate_edge_lane_common_v1 import undirected_pair_key

DEFAULT_CANONICAL = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_PENDING_PATHS = [
    ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_ann_lite_v1.jsonl",
    ROOT / "docs/final/artifacts/bible_meaning_graph_edges_approved_pending_v1.jsonl",
]
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_canonical_merge_v1_latest.json"
BUNDLE_SCRIPT = ROOT / "scripts/build_logos_corpus_graph_bundle_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _existing_pairs(canonical_path: Path) -> set[tuple[str, str]]:
    pairs: set[tuple[str, str]] = set()
    for row in _load_jsonl(canonical_path):
        src = str(row.get("src_node_id") or "")
        dst = str(row.get("dst_node_id") or "")
        if src and dst:
            pairs.add(undirected_pair_key(src, dst))
    return pairs


def _to_canonical_row(candidate: dict[str, Any], *, lane: str) -> dict[str, Any]:
    basis = candidate.get("relation_basis") or []
    evidence = candidate.get("evidence") or (
        f"promoted_pending:{lane}; edge_type={candidate.get('edge_type')}; [HYPO]"
    )
    return {
        "schema": "bible_meaning_graph_edge_v1",
        "src_node_id": candidate["src_node_id"],
        "dst_node_id": candidate["dst_node_id"],
        "edge_type": "theme_association",
        "weight": round(float(candidate.get("weight", 0.5)), 6),
        "source": "apply_logos_approved_pending_to_canonical_v1",
        "promoted_from": candidate.get("schema"),
        "promoted_lane": lane,
        "research_only": True,
        "promotion_required": True,
        "source_track": "B",
        "hypothesis_tier": "B",
        "relation_basis": basis if isinstance(basis, list) else [],
        "evidence": evidence,
        "as_of_utc": _utc_now(),
    }


def merge_pending_to_canonical(
    pending_paths: list[Path],
    canonical_path: Path,
) -> dict[str, Any]:
    existing = _existing_pairs(canonical_path)
    before_count = len(existing)
    appended: list[dict[str, Any]] = []
    skipped_duplicate = 0
    skipped_invalid = 0
    by_lane: dict[str, int] = {}

    for pending in pending_paths:
        lane = "ann_lite" if "ann_lite" in pending.name else "offline_4d_knn"
        for row in _load_jsonl(pending):
            src = str(row.get("src_node_id") or "")
            dst = str(row.get("dst_node_id") or "")
            if not src or not dst:
                skipped_invalid += 1
                continue
            key = undirected_pair_key(src, dst)
            if key in existing:
                skipped_duplicate += 1
                continue
            existing.add(key)
            canonical_row = _to_canonical_row(row, lane=lane)
            appended.append(canonical_row)
            by_lane[lane] = by_lane.get(lane, 0) + 1

    if appended:
        canonical_path.parent.mkdir(parents=True, exist_ok=True)
        with canonical_path.open("a", encoding="utf-8") as fh:
            for row in appended:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    after_count = before_count + len(appended)
    return {
        "schema": "logos_candidate_edge_canonical_merge_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "hypothesis_tier": "B",
        "canonical_path": str(canonical_path.resolve()).replace("\\", "/"),
        "canonical_pairs_before": before_count,
        "canonical_pairs_after": after_count,
        "appended_count": len(appended),
        "appended_by_lane": by_lane,
        "skipped_duplicate": skipped_duplicate,
        "skipped_invalid": skipped_invalid,
        "pending_inputs": [str(p.resolve()).replace("\\", "/") for p in pending_paths if p.is_file()],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--canonical-edges-jsonl", type=Path, default=DEFAULT_CANONICAL)
    ap.add_argument("--pending-jsonl", type=Path, action="append", default=None)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--acknowledge-canonical-risk", action="store_true")
    ap.add_argument("--refresh-bundle", action="store_true")
    args = ap.parse_args()

    if not args.acknowledge_canonical_risk:
        print("refused: --acknowledge-canonical-risk required", file=sys.stderr)
        return 3

    canonical_path = (
        args.canonical_edges_jsonl
        if args.canonical_edges_jsonl.is_absolute()
        else ROOT / args.canonical_edges_jsonl
    )
    pending_paths = list(args.pending_jsonl or DEFAULT_PENDING_PATHS)
    pending_paths = [p if p.is_absolute() else ROOT / p for p in pending_paths]

    if not canonical_path.is_file():
        print(f"Missing canonical edges: {canonical_path}", file=sys.stderr)
        return 2

    present = [p for p in pending_paths if p.is_file()]
    if not present:
        print("No pending JSONL files found", file=sys.stderr)
        return 2

    doc = merge_pending_to_canonical(present, canonical_path)
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))

    if args.refresh_bundle and BUNDLE_SCRIPT.is_file():
        proc = subprocess.run(
            [sys.executable, str(BUNDLE_SCRIPT)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            return proc.returncode

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
