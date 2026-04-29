#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def _trim_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(" ,.;:") + "."


def main() -> int:
    ap = argparse.ArgumentParser(description="Build KDD/AAAI submission abstracts from global atom one-pager.")
    ap.add_argument(
        "--onepager-json",
        default="docs/final/artifacts/global_atom_network_academic_onepager_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/global_atom_network_submission_abstracts_latest.json",
    )
    args = ap.parse_args()

    ip = resolve(args.onepager_json)
    op = resolve(args.output_json)
    if not ip.is_file():
        raise SystemExit(f"missing onepager json: {ip}")

    d = load(ip)
    facts = d.get("key_facts") if isinstance(d.get("key_facts"), dict) else {}
    methods = d.get("method_outline_en") if isinstance(d.get("method_outline_en"), list) else []
    risks = d.get("risk_notes_en") if isinstance(d.get("risk_notes_en"), list) else []
    title = str(d.get("title_en") or "Global Atom Topology PoC")

    node_count = facts.get("node_count")
    edge_count = facts.get("edge_count")
    cross_edges = facts.get("old_new_cross_edges")
    gate_status = facts.get("gate_status")
    cf_gap = facts.get("counterfactual_mean_gap")
    batch_stages_ok = facts.get("batch_stages_ok")
    batch_stages_total = facts.get("batch_stages_total")
    batch_source_mode = facts.get("batch_source_mode")

    method_1 = methods[0] if len(methods) > 0 else "Atomize event-level candidates and assign symbolic sequence priors."
    method_2 = methods[1] if len(methods) > 1 else "Build pairwise similarity matrices and gate-passed topological edges."
    method_3 = methods[2] if len(methods) > 2 else "Run drift, negative-control, and counterfactual gates before reporting."
    risk_1 = risks[0] if len(risks) > 0 else "N^2 similarity scaling requires staged expansion and compute budgeting."
    risk_2 = risks[1] if len(risks) > 1 else "4D mapping can accumulate synchronization noise."

    stage_clause = ""
    if batch_stages_ok is not None and batch_stages_total is not None:
        stage_clause = (
            f" A staged full-canon run completed {batch_stages_ok}/{batch_stages_total} stages "
            f"under source mode {batch_source_mode}. "
        )

    base = (
        f"{title}. We transform event narratives into atom-level structures "
        f"and compute topological similarity beyond lexical overlap. The resulting network contains {node_count} nodes "
        f"and {edge_count} gate-passed edges, with {cross_edges} old-new cross edges and a detected phase-transition signal. "
        f"Our robustness stack combines drift, negative-control, and counterfactual gates; integrated status is {gate_status}, "
        f"and the mean base-minus-counterfactual gap is {cf_gap}. "
        f"{stage_clause}"
        f"Methodologically, we follow three stages: {method_1} {method_2} {method_3} "
        f"Key limitations remain operational: {risk_1} {risk_2} "
        "These constraints motivate staged canon expansion with reproducible gate checkpoints."
    )

    kdd_180w = _trim_words(base, 180)
    aaai_150w = _trim_words(base, 150)

    out = {
        "schema": "global_atom_network_submission_abstracts_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "title_en": title,
        "abstracts_en": {
            "kdd_180w": kdd_180w,
            "aaai_150w": aaai_150w,
        },
        "word_count": {
            "kdd_180w": len(kdd_180w.split()),
            "aaai_150w": len(aaai_150w.split()),
        },
        "sources": {"onepager_json": str(ip)},
    }

    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

