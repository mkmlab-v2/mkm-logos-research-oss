#!/usr/bin/env python3
"""Apply logos_chronology_v1 to graph edges, symbolic map windows, and showroom overlay ([HYPO] B-track)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHRONOLOGY = ROOT / "docs/final/artifacts/fixtures/logos_chronology_v1.example.json"
DEFAULT_NODES = ROOT / "docs/final/artifacts/bible_meaning_graph_nodes_v1.jsonl"
DEFAULT_EDGES = ROOT / "docs/final/artifacts/bible_meaning_graph_edges_v1.jsonl"
DEFAULT_SYMBOLIC = ROOT / "docs/final/artifacts/logos_symbolic_event_map_v1.json"
DEFAULT_OVERLAY_OUT = ROOT / "docs/final/artifacts/logos_chronology_showroom_overlay_v1_latest.json"
DEFAULT_REPORT_OUT = ROOT / "docs/final/artifacts/logos_chronology_merge_report_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _write_json(path: Path, doc: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s:
            continue
        row = json.loads(s)
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _append_jsonl(path: Path, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    return len(rows)


def _era_node_id(era_id: str) -> str:
    return f"era::{era_id}"


def _build_graph_append_rows(chrono: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    for era in chrono.get("eras") or []:
        if not isinstance(era, dict):
            continue
        era_id = str(era.get("era_id") or "").strip()
        if not era_id:
            continue
        nid = _era_node_id(era_id)
        nodes.append(
            {
                "schema": "bible_meaning_graph_node_v1",
                "node_id": nid,
                "kind": "theme",
                "label": str(era.get("label_ko") or era_id),
                "chronology_era_id": era_id,
                "interpretation_class": era.get("interpretation_class", "[HYPO]"),
                "source": "logos_chronology_v1",
            }
        )
        for ref in list(era.get("verse_refs") or [])[:8]:
            edges.append(
                {
                    "schema": "bible_meaning_graph_edge_v1",
                    "src_node_id": str(ref),
                    "dst_node_id": nid,
                    "edge_type": "theme_association",
                    "weight": 0.72,
                    "chronology_link": "verse_to_era",
                }
            )
        for tag in list(era.get("regime_tags_observational") or [])[:3]:
            rid = f"regime::{tag}"
            nodes.append(
                {
                    "schema": "bible_meaning_graph_node_v1",
                    "node_id": rid,
                    "kind": "regime",
                    "label": str(tag),
                    "source": "logos_chronology_v1",
                }
            )
            edges.append(
                {
                    "schema": "bible_meaning_graph_edge_v1",
                    "src_node_id": nid,
                    "dst_node_id": rid,
                    "edge_type": "regime_projection",
                    "weight": 0.65,
                    "chronology_link": "era_to_regime_observational",
                }
            )
    return nodes, edges


def _build_overlay(chrono: dict[str, Any]) -> dict[str, Any]:
    era_nodes: list[dict[str, Any]] = []
    for era in chrono.get("eras") or []:
        if not isinstance(era, dict):
            continue
        era_id = str(era.get("era_id") or "")
        if not era_id:
            continue
        era_nodes.append(
            {
                "id": _era_node_id(era_id),
                "label": era.get("label_ko") or era_id,
                "kind": "era",
                "interpretation_class": era.get("interpretation_class", "[HYPO]"),
                "verse_refs": list(era.get("verse_refs") or []),
                "theme_tags": list(era.get("theme_tags") or []),
            }
        )
    bridges = [b for b in (chrono.get("modern_bridges") or []) if isinstance(b, dict)]
    return {
        "schema": "logos_chronology_showroom_overlay_v1",
        "schema_version": "1.0.0",
        "generated_at_utc": _now(),
        "hypothesis_tier": "[HYPO]",
        "research_only": True,
        "policy": chrono.get("policy"),
        "eras": chrono.get("eras") or [],
        "modern_bridges": bridges,
        "era_nodes": era_nodes,
        "field_observation_ko": (
            "연대기 레이어는 관측·해설용입니다. 1차 실물 레짐(regime_map)이 주이며 "
            "성경·연대기는 보(NON_GATING)입니다."
        ),
    }


def _patch_symbolic_map(symbolic: dict[str, Any], chrono: dict[str, Any]) -> tuple[dict[str, Any], int]:
    out = json.loads(json.dumps(symbolic))
    windows = list(out.get("chronology_windows") or [])
    by_id = {str(w.get("window_id")): w for w in windows if isinstance(w, dict) and w.get("window_id")}
    added = 0
    for bridge in chrono.get("modern_bridges") or []:
        if not isinstance(bridge, dict) or bridge.get("bridge_kind") != "chronology_window":
            continue
        wid = str(bridge.get("window_id") or "")
        if not wid or wid in by_id:
            continue
        by_id[wid] = {
            "window_id": wid,
            "start_date": "1900-01-01",
            "end_date": "2999-12-31",
            "score_multiplier": float(bridge.get("resonance_weight") or 1.0),
            "source": "logos_chronology_v1",
            "placeholder_dates": True,
        }
        added += 1
    out["chronology_windows"] = list(by_id.values())
    return out, added


def main() -> int:
    ap = argparse.ArgumentParser(description="Apply logos_chronology_v1 to graph/symbolic/showroom overlay.")
    ap.add_argument("--chronology-json", type=Path, default=DEFAULT_CHRONOLOGY)
    ap.add_argument("--nodes-jsonl", type=Path, default=DEFAULT_NODES)
    ap.add_argument("--edges-jsonl", type=Path, default=DEFAULT_EDGES)
    ap.add_argument("--symbolic-map-json", type=Path, default=DEFAULT_SYMBOLIC)
    ap.add_argument("--overlay-out", type=Path, default=DEFAULT_OVERLAY_OUT)
    ap.add_argument("--report-out", type=Path, default=DEFAULT_REPORT_OUT)
    ap.add_argument("--write-graph-append", action="store_true", help="Append era nodes/edges to graph JSONL")
    ap.add_argument("--patch-symbolic-map", action="store_true", help="Write patched symbolic map (dry-run default off)")
    ap.add_argument("--symbolic-map-out", type=Path, default=ROOT / "docs/final/artifacts/logos_symbolic_event_map_chronology_patch_v1.json")
    args = ap.parse_args()

    chrono_path = args.chronology_json if args.chronology_json.is_absolute() else ROOT / args.chronology_json
    chrono = _read_json(chrono_path)
    if chrono.get("schema") != "logos_chronology_v1":
        raise SystemExit(f"unexpected schema: {chrono.get('schema')}")

    overlay = _build_overlay(chrono)
    overlay_path = args.overlay_out if args.overlay_out.is_absolute() else ROOT / args.overlay_out
    _write_json(overlay_path, overlay)

    nodes_append, edges_append = _build_graph_append_rows(chrono)
    appended_nodes = 0
    appended_edges = 0
    if args.write_graph_append:
        nodes_path = args.nodes_jsonl if args.nodes_jsonl.is_absolute() else ROOT / args.nodes_jsonl
        edges_path = args.edges_jsonl if args.edges_jsonl.is_absolute() else ROOT / args.edges_jsonl
        appended_nodes = _append_jsonl(nodes_path, nodes_append)
        appended_edges = _append_jsonl(edges_path, edges_append)

    symbolic_added = 0
    symbolic_out_path = None
    if args.patch_symbolic_map:
        sym_path = args.symbolic_map_json if args.symbolic_map_json.is_absolute() else ROOT / args.symbolic_map_json
        symbolic = _read_json(sym_path)
        patched, symbolic_added = _patch_symbolic_map(symbolic, chrono)
        symbolic_out_path = args.symbolic_map_out if args.symbolic_map_out.is_absolute() else ROOT / args.symbolic_map_out
        _write_json(symbolic_out_path, patched)

    report = {
        "schema": "logos_chronology_merge_report_v1",
        "generated_at_utc": _now(),
        "source_chronology": str(chrono_path.resolve()),
        "overlay_path": str(overlay_path.resolve()),
        "era_count": len(chrono.get("eras") or []),
        "bridge_count": len(chrono.get("modern_bridges") or []),
        "graph_append": {
            "enabled": bool(args.write_graph_append),
            "nodes_appended": appended_nodes,
            "edges_appended": appended_edges,
            "planned_node_rows": len(nodes_append),
            "planned_edge_rows": len(edges_append),
        },
        "symbolic_map_patch": {
            "enabled": bool(args.patch_symbolic_map),
            "windows_added": symbolic_added,
            "output_path": str(symbolic_out_path.resolve()) if symbolic_out_path else None,
        },
        "track_wall": {"research_only": True, "non_gating": True, "no_trade_signals": True},
    }
    report_path = args.report_out if args.report_out.is_absolute() else ROOT / args.report_out
    _write_json(report_path, report)
    print(str(overlay_path))
    print(str(report_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
