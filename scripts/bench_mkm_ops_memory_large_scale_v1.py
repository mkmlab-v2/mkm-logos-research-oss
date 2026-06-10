#!/usr/bin/env python3
"""Large-scale MKM ops memory bench — Prism registry pool + drift mutations ([HYPO]).

B-track research only. Expands registry paths × query templates × chunk variants ×
drift mutations to reach n>=1000 without mutating repo files.

  py scripts/bench_mkm_ops_memory_large_scale_v1.py
  py scripts/bench_mkm_ops_memory_large_scale_v1.py --min-scenarios 50 --smoke

Output: reports/mkm_ops_memory_large_scale_bench_v1_latest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import re
import sys
import time
from itertools import product
from pathlib import Path
from statistics import mean
from typing import Any

from mkm_ops_memory_index_lib_v1 import (
    DEFAULT_INDEX_PATH,
    DEFAULT_REPAIR_MAX_TOTAL_CHARS,
    DEFAULT_REPAIR_SLICE_MAX_CHARS,
    DEFAULT_ROUTE_MAX_NODES,
    assemble_ops_memory_pins_text,
    assemble_ops_memory_repair_v2_text,
    build_web_ops_overlay_nodes,
    compute_node_sha_prefix,
    extract_node_from_index,
    load_index,
    missing_must_keep_tags,
    prism_axis_field_tag,
    resolve_path,
    route_nodes_by_field_tags,
    truncate_anchor_slice,
    utc_now_iso,
    verify_index_sha_drift,
)

SCRIPT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = SCRIPT_ROOT / "docs/final/MKM12_PRISM_INDEX_REGISTRY_V1.json"
DEFAULT_GATE = SCRIPT_ROOT / "docs/final/artifacts/web_ops_regime_gate_v1_latest.json"
DEFAULT_OUT = SCRIPT_ROOT / "reports/mkm_ops_memory_large_scale_bench_v1_latest.json"

CHUNK_SIZES = (400, 800, 1200)
MUTATIONS = (
    "baseline",
    "stale_sha",
    "header_drop",
    "wrong_json_pointer",
    "chunk_tight",
    "chunk_wide",
)
QUERY_TEMPLATES = (
    "{summary}",
    "{id} prism {axis} SSOT",
    "{basename} Fact-Lock gate research_only",
    "web_ops regime gate {axis}",
    "must_keep_tags drift sha {id}",
    "coordinate json_pointer {basename}",
    "Nebius cost audit HOLD payment",
    "infra GPU ollama vps lane",
    "oracle prophecy inception align",
    "MS defense submission HOLD",
)

SCHEMA = "mkm_ops_memory_large_scale_bench_v1"


def _count_tokens(text: str) -> dict[str, Any]:
    try:
        import tiktoken

        enc = tiktoken.get_encoding("cl100k_base")
        return {"tokens": len(enc.encode(text)), "method": "tiktoken:cl100k_base"}
    except Exception as exc:  # noqa: BLE001
        est = max(1, len(text) // 4)
        return {"tokens": est, "method": "char_div_4_estimate", "note": str(exc)}


def _token_set(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z0-9_가-힣$]+", text.lower()))


def jaccard(a: str, b: str) -> float:
    sa, sb = _token_set(a), _token_set(b)
    if not sa and not sb:
        return 1.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def _peak_rss_kb() -> int | None:
    try:
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    except Exception:  # noqa: BLE001
        return None


def _percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((pct / 100.0) * (len(ordered) - 1)))))
    return round(ordered[idx], 4)


def _load_registry_entries(registry_path: Path) -> list[dict[str, Any]]:
    doc = json.loads(registry_path.read_text(encoding="utf-8-sig"))
    return list(doc.get("entries") or [])


def _registry_entry_to_node(entry: dict[str, Any]) -> dict[str, Any]:
    axis = str(entry.get("prism_axis") or "S")
    entry_id = str(entry.get("id") or "")
    return {
        "file_path": entry["path"],
        "slice_kind": "registry_chunk",
        "essence": entry.get("summary_ko") or entry_id,
        "must_keep_tags": ["research_only"],
        "priority": 5,
        "field_tags": [prism_axis_field_tag(axis), entry_id],
        "prism_registry_id": entry_id,
    }


def build_expanded_index(
    root: Path,
    *,
    index_path: Path,
    registry_path: Path,
    include_web_ops_overlay: bool = True,
) -> dict[str, Any]:
    base = load_index(index_path)
    nodes = dict(base.get("nodes") or {})
    if include_web_ops_overlay:
        nodes.update(build_web_ops_overlay_nodes(root))
    for entry in _load_registry_entries(registry_path):
        rel = entry.get("path")
        if not rel or not (root / rel).is_file():
            continue
        node_id = f"prism_reg_{entry['id']}"
        nodes[node_id] = _registry_entry_to_node(entry)
    merged = dict(base)
    merged["nodes"] = nodes
    merged["pool_sources"] = {
        "ops_index": str(index_path),
        "registry": str(registry_path),
        "registry_nodes_added": sum(1 for k in nodes if k.startswith("prism_reg_")),
    }
    return merged


def _chunk_for_mutation(mutation: str, default: int) -> int:
    if mutation == "chunk_tight":
        return 400
    if mutation == "chunk_wide":
        return 1200
    return default


def _extract_registry_chunk(
    root: Path,
    node: dict[str, Any],
    *,
    max_chars: int,
    mutation: str,
) -> str:
    if mutation == "missing_file":
        raise FileNotFoundError(f"simulated missing: {node.get('file_path')}")
    path = resolve_path(root, node["file_path"])
    if not path.is_file():
        raise FileNotFoundError(f"Missing indexed file: {node['file_path']}")
    text = path.read_text(encoding="utf-8", errors="replace")
    if mutation == "header_drop" and text:
        lines = text.splitlines()
        text = "\n".join(lines[1:]) if len(lines) > 1 else text
    preview, _ = truncate_anchor_slice(text, max_chars=max_chars)
    return preview


def _pins_text_mutation(
    root: Path,
    nodes: list[tuple[str, dict[str, Any]]],
    *,
    include_slice: bool,
    slice_max_chars: int,
    query: str,
    mutation: str,
    coordinate_filter: bool = False,
) -> str:
    """Mutation-aware assembly — drift mutations still pass relevance + Jaccard gate."""
    if include_slice:
        return assemble_ops_memory_repair_v2_text(
            root,
            nodes,
            slice_max_chars=slice_max_chars,
            query=query,
            coordinate_filter=coordinate_filter,
            max_total_chars=DEFAULT_REPAIR_MAX_TOTAL_CHARS,
            mutation=mutation,
            noise_guard=True,
        )
    return assemble_ops_memory_pins_text(
        root,
        nodes,
        include_slice=False,
        max_total_chars=DEFAULT_REPAIR_MAX_TOTAL_CHARS,
        mutation=mutation,
    )


def _format_query(template: str, entry: dict[str, Any] | None, *, fallback_id: str) -> str:
    if entry:
        path = entry.get("path") or ""
        basename = Path(path).name
        return template.format(
            summary=entry.get("summary_ko") or entry.get("id") or fallback_id,
            id=entry.get("id") or fallback_id,
            axis=entry.get("prism_axis") or "S",
            basename=basename or fallback_id,
        )
    return template.format(
        summary=fallback_id,
        id=fallback_id,
        axis="S",
        basename=fallback_id,
    )


def _live_sha_prefix(root: Path, node: dict[str, Any]) -> str | None:
    try:
        if node.get("slice_kind") == "registry_chunk":
            block = _extract_registry_chunk(
                root, node, max_chars=8000, mutation="baseline"
            )
            return hashlib.sha256(block.encode("utf-8")).hexdigest()[:16]
        return compute_node_sha_prefix(root, node)
    except (FileNotFoundError, ValueError, json.JSONDecodeError, KeyError):
        return None


def _simulate_stale_sha_drift(
    root: Path,
    node: dict[str, Any],
) -> tuple[bool, str | None]:
    """Return (drift_detected, error_message). Does not mutate index on disk."""
    live = _live_sha_prefix(root, node)
    if not live:
        return False, None
    fake = hashlib.sha256(b"stale_bench_mutation").hexdigest()[:16]
    if fake == live:
        return False, None
    return True, f"stale_sha: stored={fake} live={live}"


def _generate_scenario_specs(
    registry_entries: list[dict[str, Any]],
    *,
    min_scenarios: int,
    seed: int,
) -> list[dict[str, Any]]:
    existing = [e for e in registry_entries if e.get("path")]
    rng = random.Random(seed)
    specs: list[dict[str, Any]] = []
    seq = 0
    for entry, template, mutation, chunk in product(
        existing,
        QUERY_TEMPLATES,
        MUTATIONS,
        CHUNK_SIZES,
    ):
        if len(specs) >= min_scenarios:
            break
        query = _format_query(template, entry, fallback_id=f"node_{seq}")
        specs.append(
            {
                "scenario_id": f"ls_{seq:05d}",
                "registry_id": entry.get("id"),
                "query": query,
                "mutation": mutation,
                "chunk_size": _chunk_for_mutation(mutation, chunk),
                "anchor_entry_path": entry.get("path"),
            }
        )
        seq += 1
    # Pad with ops-only web_ops query clones if registry pool too small
    while len(specs) < min_scenarios:
        template = rng.choice(QUERY_TEMPLATES)
        entry = rng.choice(existing) if existing else None
        mutation = rng.choice(MUTATIONS)
        chunk = rng.choice(CHUNK_SIZES)
        query = _format_query(template, entry, fallback_id=f"pad_{seq}")
        specs.append(
            {
                "scenario_id": f"ls_{seq:05d}",
                "registry_id": entry.get("id") if entry else None,
                "query": query,
                "mutation": mutation,
                "chunk_size": _chunk_for_mutation(mutation, chunk),
                "anchor_entry_path": entry.get("path") if entry else None,
            }
        )
        seq += 1
    rng.shuffle(specs)
    return specs


def _evaluate_scenario(
    root: Path,
    index: dict[str, Any],
    spec: dict[str, Any],
) -> dict[str, Any]:
    query = spec["query"]
    mutation = spec["mutation"]
    chunk = int(spec["chunk_size"])
    t0 = time.perf_counter()
    routed = route_nodes_by_field_tags(index, query)
    lookup_ms = (time.perf_counter() - t0) * 1000.0

    raw_text = assemble_ops_memory_pins_text(
        root,
        routed,
        include_slice=False,
        max_total_chars=None,
    )
    repair_text = _pins_text_mutation(
        root,
        routed,
        include_slice=True,
        slice_max_chars=min(chunk, DEFAULT_REPAIR_SLICE_MAX_CHARS),
        query=query,
        mutation=mutation,
    )
    coord_text = _pins_text_mutation(
        root,
        routed,
        include_slice=True,
        slice_max_chars=min(chunk, DEFAULT_REPAIR_SLICE_MAX_CHARS),
        query=query,
        mutation=mutation,
        coordinate_filter=True,
    )

    raw_tok = _count_tokens(raw_text)["tokens"]
    repair_tok = _count_tokens(repair_text)["tokens"]
    coord_tok = _count_tokens(coord_text)["tokens"]
    raw_j = jaccard(query, raw_text)
    repair_j = jaccard(query, repair_text)
    coord_j = jaccard(query, coord_text)

    must_keep_failures: list[str] = []
    for node_id, node in routed:
        missing = missing_must_keep_tags(repair_text, node.get("must_keep_tags") or [])
        if missing:
            must_keep_failures.append(f"{node_id}:{missing}")

    drift_detected = False
    drift_notes: list[str] = []
    if mutation == "stale_sha":
        for node_id, node in routed[:3]:
            detected, msg = _simulate_stale_sha_drift(root, node)
            if detected and msg:
                drift_detected = True
                drift_notes.append(f"{node_id}:{msg}")

    return {
        "scenario_id": spec["scenario_id"],
        "registry_id": spec.get("registry_id"),
        "mutation": mutation,
        "chunk_size": chunk,
        "query": query[:200],
        "routed_count": len(routed),
        "lookup_ms": round(lookup_ms, 4),
        "raw": {"tokens": raw_tok, "jaccard_vs_query": round(raw_j, 4)},
        "repair_v2": {
            "tokens": repair_tok,
            "jaccard_vs_query": round(repair_j, 4),
            "operational_label": "post-processor included",
        },
        "coordinate_v1": {
            "tokens": coord_tok,
            "jaccard_vs_query": round(coord_j, 4),
        },
        "delta": {
            "jaccard_repair_v2_minus_raw": round(repair_j - raw_j, 4),
            "jaccard_coordinate_v1_minus_raw": round(coord_j - raw_j, 4),
            "tokens_repair_minus_raw": repair_tok - raw_tok,
        },
        "must_keep_inject_ok": len(must_keep_failures) == 0,
        "must_keep_failures": must_keep_failures[:3],
        "drift_detected": drift_detected,
        "drift_notes": drift_notes[:2],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=SCRIPT_ROOT)
    ap.add_argument("--index", type=Path, default=DEFAULT_INDEX_PATH)
    ap.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--min-scenarios", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--smoke", action="store_true", help="Shortcut for --min-scenarios 50")
    ap.add_argument(
        "--sample-scenarios-in-out",
        type=int,
        default=24,
        help="Max scenario rows embedded in JSON (aggregate always full)",
    )
    args = ap.parse_args()
    if args.smoke:
        args.min_scenarios = 50

    root = args.workspace_root.resolve()
    index = build_expanded_index(
        root,
        index_path=args.index,
        registry_path=args.registry,
    )
    registry_entries = _load_registry_entries(args.registry)
    existing_registry = [
        e for e in registry_entries if e.get("path") and (root / e["path"]).is_file()
    ]

    source_errors = []
    try:
        from mkm_ops_memory_index_lib_v1 import verify_index_sources

        source_errors = verify_index_sources(root, index)
    except Exception as exc:  # noqa: BLE001
        source_errors = [str(exc)]

    sha_drift_errors = verify_index_sha_drift(root, index)

    specs = _generate_scenario_specs(
        existing_registry,
        min_scenarios=max(1, args.min_scenarios),
        seed=args.seed,
    )

    rows: list[dict[str, Any]] = []
    lookup_ms_list: list[float] = []
    raw_j_list: list[float] = []
    repair_j_list: list[float] = []
    coord_j_list: list[float] = []
    raw_tok_list: list[int] = []
    repair_tok_list: list[int] = []
    coord_tok_list: list[int] = []
    must_keep_pass = 0
    drift_hits = 0

    for spec in specs:
        row = _evaluate_scenario(root, index, spec)
        rows.append(row)
        lookup_ms_list.append(float(row["lookup_ms"]))
        raw_j_list.append(float(row["raw"]["jaccard_vs_query"]))
        repair_j_list.append(float(row["repair_v2"]["jaccard_vs_query"]))
        coord_j_list.append(float(row["coordinate_v1"]["jaccard_vs_query"]))
        raw_tok_list.append(int(row["raw"]["tokens"]))
        repair_tok_list.append(int(row["repair_v2"]["tokens"]))
        coord_tok_list.append(int(row["coordinate_v1"]["tokens"]))
        if row["must_keep_inject_ok"]:
            must_keep_pass += 1
        if row["drift_detected"]:
            drift_hits += 1

    full_gate_text = ""
    if args.gate_json.is_file():
        full_gate_text = args.gate_json.read_text(encoding="utf-8-sig")
    full_gate_tok = _count_tokens(full_gate_text)["tokens"] if full_gate_text else 0
    avg_raw_tok = mean(raw_tok_list) if raw_tok_list else 0.0

    sample_n = max(0, args.sample_scenarios_in_out)
    scenario_sample = rows[:sample_n] if sample_n else []
    pinset_top = sorted(
        rows,
        key=lambda row: int(row["repair_v2"]["tokens"]),
        reverse=True,
    )[:3]
    pinset_worst_jaccard = sorted(
        rows,
        key=lambda row: float(row["delta"]["jaccard_repair_v2_minus_raw"]),
    )[:3]

    doc: dict[str, Any] = {
        "schema": SCHEMA,
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "boundary_ack": "[HYPO] large-scale registry pool — not Track A·live merge",
        "generated_at_utc": utc_now_iso(),
        "seed": args.seed,
        "scenario_count": len(rows),
        "pool": {
            "registry_entries_total": len(registry_entries),
            "registry_paths_existing": len(existing_registry),
            "index_nodes_total": len(index.get("nodes") or {}),
            "pool_sources": index.get("pool_sources"),
        },
        "gates": {
            "verify_index_sources_errors": len(source_errors),
            "verify_index_sha_drift_errors": len(sha_drift_errors),
            "must_keep_inject_pass_count": must_keep_pass,
            "must_keep_inject_pass_rate": round(must_keep_pass / len(rows), 4) if rows else None,
            "stale_sha_drift_detected_count": drift_hits,
        },
        "sre": {
            "lookup_ms_p50": _percentile(lookup_ms_list, 50),
            "lookup_ms_p95": _percentile(lookup_ms_list, 95),
            "lookup_ms_p99": _percentile(lookup_ms_list, 99),
            "peak_rss_kb": _peak_rss_kb(),
        },
        "full_gate_json": {
            "path": str(args.gate_json),
            "tokens": full_gate_tok,
            "present": bool(full_gate_text),
        },
        "aggregate": {
            "raw": {
                "mean_jaccard_vs_query": round(mean(raw_j_list), 4) if raw_j_list else None,
                "mean_tokens_per_scenario": round(avg_raw_tok, 2),
            },
            "repair_v2": {
                "mean_jaccard_vs_query": round(mean(repair_j_list), 4) if repair_j_list else None,
                "mean_tokens_per_scenario": round(mean(repair_tok_list), 2) if repair_tok_list else None,
                "operational_label": "post-processor included",
            },
            "coordinate_v1": {
                "mean_jaccard_vs_query": round(mean(coord_j_list), 4) if coord_j_list else None,
                "mean_tokens_per_scenario": round(mean(coord_tok_list), 2) if coord_tok_list else None,
            },
            "delta": {
                "mean_jaccard_repair_v2_minus_raw": round(
                    mean(repair_j_list) - mean(raw_j_list), 4
                )
                if raw_j_list and repair_j_list
                else None,
                "mean_jaccard_coordinate_v1_minus_raw": round(
                    mean(coord_j_list) - mean(raw_j_list), 4
                )
                if raw_j_list and coord_j_list
                else None,
                "tokens_saved_vs_full_gate_json": (
                    full_gate_tok - int(avg_raw_tok) if full_gate_tok else None
                ),
                "reduction_ratio_vs_full_gate": (
                    round(1 - (avg_raw_tok / full_gate_tok), 4) if full_gate_tok else None
                ),
            },
        },
        "pinset_top_repair_tokens": pinset_top,
        "pinset_worst_jaccard_delta": pinset_worst_jaccard,
        "scenario_sample": scenario_sample,
        "scenario_sample_note": (
            f"first {len(scenario_sample)} of {len(rows)}; use --sample-scenarios-in-out 0 "
            "for aggregate-only output"
        ),
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out),
                "scenario_count": len(rows),
                "aggregate": doc["aggregate"],
                "gates": doc["gates"],
                "sre": doc["sre"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
