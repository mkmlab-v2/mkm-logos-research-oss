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


def main() -> int:
    ap = argparse.ArgumentParser(description="Build KDD submission template from global atom artifacts.")
    ap.add_argument(
        "--onepager-json",
        default="docs/final/artifacts/global_atom_network_academic_onepager_latest.json",
    )
    ap.add_argument(
        "--abstracts-json",
        default="docs/final/artifacts/global_atom_network_submission_abstracts_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/global_atom_kdd_submission_template_latest.json",
    )
    args = ap.parse_args()

    opg = resolve(args.onepager_json)
    apj = resolve(args.abstracts_json)
    outp = resolve(args.output_json)
    for p in (opg, apj):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    one = load(opg)
    abs_doc = load(apj)
    facts = one.get("key_facts") if isinstance(one.get("key_facts"), dict) else {}
    method = one.get("method_outline_en") if isinstance(one.get("method_outline_en"), list) else []
    risks = one.get("risk_notes_en") if isinstance(one.get("risk_notes_en"), list) else []
    stage_breakdown = one.get("stage_breakdown") if isinstance(one.get("stage_breakdown"), list) else []
    run_lineage = one.get("run_lineage") if isinstance(one.get("run_lineage"), dict) else {}
    title = str(abs_doc.get("title_en") or one.get("title_en") or "").strip()
    kdd_abstract = str(((abs_doc.get("abstracts_en") or {}).get("kdd_180w")) or "").strip()

    keywords = [
        "topological knowledge graph",
        "digital humanities",
        "symbolic atomization",
        "counterfactual robustness",
        "cross-domain event similarity",
    ]
    batch_stages_total = facts.get("batch_stages_total")
    if batch_stages_total:
        contrib_2 = "Demonstrates staged full-canon execution with measurable transition links and gated topology outputs."
    else:
        contrib_2 = "Demonstrates core-100 PoC with measurable old-new transition links and gated topology outputs."
    contributions = [
        "Introduces an atom-topology pipeline that maps event narratives to structure-level similarity beyond lexical overlap.",
        contrib_2,
        "Integrates drift, negative-control, and counterfactual gates into a reproducible robustness stack.",
    ]
    checklist = [
        "Paste title/abstract/keywords directly into KDD form fields.",
        "Attach artifact packet paths in supplementary material.",
        "Keep proprietary weights/formulas redacted; disclose only gated metrics.",
    ]

    out = {
        "schema": "global_atom_kdd_submission_template_v1",
        "generated_at_utc": now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "track": "kdd_applied_data_science",
        "title_en": title,
        "abstract_en_180w": kdd_abstract,
        "keywords_en": keywords,
        "contributions_en": contributions,
        "quick_facts": {
            "node_count": facts.get("node_count"),
            "edge_count": facts.get("edge_count"),
            "old_new_cross_edges": facts.get("old_new_cross_edges"),
            "gate_status": facts.get("gate_status"),
            "counterfactual_mean_gap": facts.get("counterfactual_mean_gap"),
            "batch_stages_ok": facts.get("batch_stages_ok"),
            "batch_stages_total": facts.get("batch_stages_total"),
            "batch_source_mode": facts.get("batch_source_mode"),
        },
        "method_outline_en": method,
        "risk_notes_en": risks,
        "stage_breakdown": stage_breakdown,
        "run_lineage": run_lineage,
        "submission_checklist_en": checklist,
        "sources": {"onepager_json": str(opg), "abstracts_json": str(apj)},
    }

    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(outp))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

