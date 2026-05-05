#!/usr/bin/env python3
# @MKM12-METADATA
# Type: Logic
# Vector: {S:0.8, L:0.8, K:0.4, M:0.5}
# Balance: 90
# Purpose: Parse external Bible cross-reference baseline into normalized edge pairs and compute initial overlap metrics.
# Keywords: parser, baseline, cross-reference, coverage_overlap, precision_at_k
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

BOOK_ALIASES = {
    "genesis": "Gen",
    "gen": "Gen",
    "exodus": "Exod",
    "exo": "Exod",
    "exod": "Exod",
    "isaiah": "Isa",
    "isa": "Isa",
    "matthew": "Matt",
    "matt": "Matt",
    "john": "John",
    "1john": "1John",
    "2john": "2John",
    "3john": "3John",
    "1cor": "1Cor",
    "2cor": "2Cor",
    "1sam": "1Sam",
    "2sam": "2Sam",
    "1kings": "1Kgs",
    "2kings": "2Kgs",
    "1chron": "1Chr",
    "2chron": "2Chr",
    "revelation": "Rev",
    "rev": "Rev",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def parse_ref_parts(ref: str) -> tuple[str, int, int] | None:
    raw = (ref or "").strip()
    if not raw:
        return None
    # Accept formats like:
    # - "Genesis 2:9"
    # - "Gen.2.9"
    # - "genesis::Gen.2.9"
    if "::" in raw:
        raw = raw.split("::", 1)[1]
    raw = raw.replace("_", " ").replace("-", " ").replace(";", ":")
    dotted = re.match(r"^\s*([1-3]?[A-Za-z]+)\.?\s*(\d+)\.(\d+)\s*$", raw)
    if dotted:
        book, chapter, verse = dotted.group(1), dotted.group(2), dotted.group(3)
    else:
        spaced = re.match(r"^\s*([1-3]?[A-Za-z]+)\s+(\d+)\s*:\s*(\d+)\s*$", raw)
        if not spaced:
            return None
        book, chapter, verse = spaced.group(1), spaced.group(2), spaced.group(3)
    key = book.lower()
    canon_book = BOOK_ALIASES.get(key, book[:1].upper() + book[1:4].lower())
    return canon_book, int(chapter), int(verse)


def normalize_ref(ref: str) -> str:
    parts = parse_ref_parts(ref)
    if not parts:
        return ""
    book, chapter, verse = parts
    return f"{book}.{chapter}.{verse}"


def expand_ref(raw_ref: str, range_mode: str) -> list[str]:
    raw = (raw_ref or "").strip()
    if not raw:
        return []
    if "-" not in raw or range_mode == "start":
        single = normalize_ref(raw.split("-", 1)[0].strip())
        return [single] if single else []

    left_raw, right_raw = [x.strip() for x in raw.split("-", 1)]
    left = parse_ref_parts(left_raw)
    right = parse_ref_parts(right_raw)
    if not left or not right:
        single = normalize_ref(left_raw)
        return [single] if single else []
    l_book, l_ch, l_vs = left
    r_book, r_ch, r_vs = right
    if l_book != r_book or l_ch != r_ch or r_vs < l_vs:
        # Cross-book/chapter ranges are ambiguous; safely fallback to range start.
        return [f"{l_book}.{l_ch}.{l_vs}"]
    return [f"{l_book}.{l_ch}.{v}" for v in range(l_vs, r_vs + 1)]


def pair_key(a: str, b: str) -> str:
    return "||".join(sorted([a, b]))


def load_external_rows(path: Path) -> list[dict[str, Any]]:
    if path.suffix.lower() == ".jsonl":
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s:
                continue
            obj = json.loads(s)
            if isinstance(obj, dict):
                rows.append(obj)
        return rows
    if path.suffix.lower() == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            return list(csv.DictReader(f))
    if path.suffix.lower() == ".txt":
        # OpenBible export is tab-delimited with headers:
        # From Verse\tTo Verse\tVotes\t#www.openbible.info ...
        rows: list[dict[str, Any]] = []
        with path.open("r", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                if not isinstance(row, dict):
                    continue
                rows.append(
                    {
                        "source_ref": row.get("From Verse", ""),
                        "target_ref": row.get("To Verse", ""),
                        "votes": row.get("Votes", ""),
                    }
                )
        return rows
    raise SystemExit("external input must be .jsonl, .csv, or .txt")


def load_internal_edges(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        obj = json.loads(s)
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def load_node_ref_map(path: Path | None) -> dict[str, str]:
    if path is None:
        return {}
    if not path.is_file():
        raise SystemExit(f"missing node ref map json: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        return {}
    data = raw
    rows = data.get("rows")
    if not isinstance(rows, list):
        return {}
    out: dict[str, str] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        node_id = str(row.get("node_id", "")).strip()
        verse_ref = str(row.get("verse_ref", "")).strip()
        if node_id and verse_ref:
            out[node_id] = verse_ref
    return out


def extract_ref(row: dict[str, Any], candidates: list[str]) -> str:
    for key in candidates:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def main() -> int:
    ap = argparse.ArgumentParser(description="Parse external baseline and compute initial overlap metrics.")
    ap.add_argument("--external-input", default="docs/final/artifacts/external_bible_crossref_seed_v1.jsonl")
    ap.add_argument("--internal-edges-jsonl", default="docs/final/artifacts/global_atom_network_edges_latest.jsonl")
    ap.add_argument("--top-k", type=int, default=1000)
    ap.add_argument("--random-trials", type=int, default=200)
    ap.add_argument("--node-ref-map-json", default="")
    ap.add_argument("--external-source-type", default="manual_editorial")
    ap.add_argument("--range-mode", choices=["start", "expand"], default="start")
    ap.add_argument("--normalized-out-jsonl", default="docs/final/artifacts/external_bible_crossref_normalized_latest.jsonl")
    ap.add_argument("--report-out-json", default="docs/final/artifacts/external_bible_crossref_overlap_report_latest.json")
    args = ap.parse_args()
    external_source_type = str(args.external_source_type or "manual_editorial").strip() or "manual_editorial"
    range_mode = str(args.range_mode or "start")

    external_path = resolve(args.external_input)
    internal_path = resolve(args.internal_edges_jsonl)
    normalized_out = resolve(args.normalized_out_jsonl)
    report_out = resolve(args.report_out_json)
    if not external_path.is_file():
        raise SystemExit(f"missing external input: {external_path}")
    if not internal_path.is_file():
        raise SystemExit(f"missing internal edges: {internal_path}")
    node_map_path = resolve(args.node_ref_map_json) if str(args.node_ref_map_json).strip() else None

    external_rows = load_external_rows(external_path)
    normalized_external: list[dict[str, Any]] = []
    external_pairs: set[str] = set()
    parse_fail_count = 0
    for row in external_rows:
        src_raw = extract_ref(row, ["source_ref", "source", "from_ref", "from"])
        dst_raw = extract_ref(row, ["target_ref", "target", "to_ref", "to"])
        src_refs = expand_ref(src_raw, range_mode)
        dst_refs = expand_ref(dst_raw, range_mode)
        if not src_refs or not dst_refs:
            parse_fail_count += 1
            continue
        for src in src_refs:
            for dst in dst_refs:
                if not src or not dst:
                    continue
                key = pair_key(src, dst)
                external_pairs.add(key)
                normalized_external.append(
                    {
                        "source_type": external_source_type,
                        "source_ref_norm": src,
                        "target_ref_norm": dst,
                        "pair_key": key,
                        "source_ref_raw": src_raw,
                        "target_ref_raw": dst_raw,
                    }
                )

    internal_rows = load_internal_edges(internal_path)
    node_ref_map = load_node_ref_map(node_map_path)
    internal_pairs: set[str] = set()
    scored_pairs: list[tuple[str, float]] = []
    internal_map_hit = 0
    internal_map_miss = 0
    for row in internal_rows:
        src_raw = extract_ref(row, ["source", "src_node_id", "src"])
        dst_raw = extract_ref(row, ["target", "dst_node_id", "dst"])
        if node_ref_map:
            if src_raw in node_ref_map:
                src_raw = node_ref_map[src_raw]
                internal_map_hit += 1
            else:
                internal_map_miss += 1
            if dst_raw in node_ref_map:
                dst_raw = node_ref_map[dst_raw]
                internal_map_hit += 1
            else:
                internal_map_miss += 1
        src_refs = expand_ref(src_raw, range_mode)
        dst_refs = expand_ref(dst_raw, range_mode)
        if not src_refs or not dst_refs:
            continue
        sim = row.get("similarity", row.get("weight", 0.0))
        try:
            score = float(sim or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        for src in src_refs:
            for dst in dst_refs:
                if not src or not dst:
                    continue
                key = pair_key(src, dst)
                internal_pairs.add(key)
                scored_pairs.append((key, score))

    overlap = external_pairs & internal_pairs
    coverage_overlap = (len(overlap) / len(external_pairs)) if external_pairs else 0.0

    top_k = max(1, int(args.top_k))
    scored_pairs.sort(key=lambda x: x[1], reverse=True)
    topk_pairs = [key for key, _ in scored_pairs[:top_k]]
    if topk_pairs:
        precision_at_k = sum(1 for key in topk_pairs if key in external_pairs) / len(topk_pairs)
    else:
        precision_at_k = 0.0

    universe = [key for key, _ in scored_pairs]
    random_precisions: list[float] = []
    sample_k = min(top_k, len(universe))
    if sample_k > 0:
        rng = random.Random(42)
        for _ in range(max(1, int(args.random_trials))):
            sampled = rng.sample(universe, sample_k)
            p = sum(1 for key in sampled if key in external_pairs) / sample_k
            random_precisions.append(p)
    random_mean = sum(random_precisions) / len(random_precisions) if random_precisions else 0.0
    delta_random_baseline = precision_at_k - random_mean

    normalized_out.parent.mkdir(parents=True, exist_ok=True)
    normalized_out.write_text(
        "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in normalized_external),
        encoding="utf-8",
    )

    report = {
        "schema": "external_bible_crossref_overlap_report_v1",
        "generated_at_utc": now_utc(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "baseline_classification": "manual_editorial_heuristic",
        "algorithmic_ground_truth": False,
        "a_track_merge_allowed": False,
        "inputs": {
            "external_input": str(external_path),
            "external_source_type": external_source_type,
            "range_mode": range_mode,
            "internal_edges_jsonl": str(internal_path),
            "node_ref_map_json": str(node_map_path) if node_map_path else None,
            "top_k": top_k,
            "random_trials": max(1, int(args.random_trials)),
        },
        "counts": {
            "external_rows_raw": len(external_rows),
            "external_rows_parsed": len(normalized_external),
            "external_rows_parse_fail": parse_fail_count,
            "external_unique_pairs": len(external_pairs),
            "internal_unique_pairs_normalized": len(internal_pairs),
            "internal_node_map_hit": internal_map_hit,
            "internal_node_map_miss": internal_map_miss,
            "overlap_pair_count": len(overlap),
        },
        "metrics": {
            "coverage_overlap": round(coverage_overlap, 6),
            "precision_at_k": round(precision_at_k, 6),
            "delta_random_baseline": round(delta_random_baseline, 6),
            "random_precision_mean": round(random_mean, 6),
        },
        "notes": [
            "External baseline rows are explicitly tagged as source_type=manual_editorial.",
            "Coverage and precision compare heterogeneous graph types; interpret as calibration-only in B-track.",
            "Low overlap does not imply model failure when corpus scope differs.",
        ],
        "sample_overlap_pairs": sorted(list(overlap))[:20],
    }
    report_out.parent.mkdir(parents=True, exist_ok=True)
    report_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(report_out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
