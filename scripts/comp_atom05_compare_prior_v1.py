#!/usr/bin/env python3
"""Merge COMP-ATOM-05 + prior GraphRAG sweep reports (B-track index)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
OUT = PILOT / "comp_atom05_compare_prior_v1.json"

SOURCES = (
    ("graphrag_philosophy_full", PILOT / "comp_graphrag_philosophy_sweep_v1.json"),
    ("graphrag_logos_subset", PILOT / "comp_graphrag_logos_subset_sweep_v1.json"),
    ("atom05_logos_subset", PILOT / "comp_atom05_graph_wire_bridge_sweep_v1.json"),
    ("atom05_full_v2", PILOT / "comp_atom05_full_v2_sweep_v1.json"),
    ("atom05_profile_matrix", PILOT / "comp_atom05_profile_matrix_sweep_v1.json"),
)


def _pick_metrics(doc: dict) -> dict:
    matrices = doc.get("matrices")
    if isinstance(matrices, list):
        out: dict = {}
        for m in matrices:
            if not isinstance(m, dict):
                continue
            label = str(m.get("bench_label") or "matrix")
            for c in m.get("cells") or []:
                if isinstance(c, dict) and c.get("cell_id"):
                    out[f"{label}/{c['cell_id']}"] = c.get("metrics") or c
        if out:
            return out
    combos = doc.get("combos")
    if isinstance(combos, list):
        return {
            c.get("combo_id", f"combo_{i}"): (c.get("metrics") or c)
            for i, c in enumerate(combos)
            if isinstance(c, dict)
        }
    if isinstance(combos, dict):
        return {k: (v.get("metrics") if isinstance(v, dict) else v) for k, v in combos.items()}
    return {}


def main() -> int:
    PILOT.mkdir(parents=True, exist_ok=True)
    merged: dict = {}
    for key, path in SOURCES:
        if not path.is_file():
            merged[key] = {"missing": str(path.relative_to(ROOT)).replace("\\", "/")}
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        merged[key] = {
            "schema": doc.get("schema"),
            "generated_at_utc": doc.get("generated_at_utc"),
            "deltas": doc.get("deltas_graphrag_vs_baseline")
            or doc.get("deltas_wire_selective_vs_baseline")
            or doc.get("deltas_wire_selective_vs_full_baseline"),
            "combos": _pick_metrics(doc),
        }

    report = {
        "schema": "comp_atom05_compare_prior_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "track_a_frozen_headline": "47.5% economy bridge_off (not modified by this report)",
        "sources": merged,
        "headline": (
            "must_keep graph anchors: delta 0 on full bench; "
            "wire_selective_bridge: +Jaccard on logos subset and selective full-v2 cases"
        ),
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT.relative_to(ROOT))}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
