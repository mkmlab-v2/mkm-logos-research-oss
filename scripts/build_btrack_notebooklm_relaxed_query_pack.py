#!/usr/bin/env python3
"""Generate a large B-Track NotebookLM query pack from seed templates.

This is for high-volume exploratory insight collection (research-only).
"""

from __future__ import annotations

import argparse
import json
from itertools import product
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_notebooklm_query_pack_relaxed_v1.json"


LENSES = [
    ("logos", "canonical + original-language anchors"),
    ("dss", "Dead Sea Scroll witnesses and fragment context"),
    ("apocrypha", "apocrypha/deuterocanon narrative motifs"),
    ("myeongri", "time/regime interpretation lens"),
    ("sasang", "human-response/constitutional reaction lens"),
]

THEMES = [
    ("transition", "crisis-to-transition structure"),
    ("warning", "early warning motifs before regime shifts"),
    ("stabilization", "stabilization / recovery motifs"),
    ("conflict", "conflict escalation and de-escalation motifs"),
    ("governance", "guardrail and governance language"),
    ("falsification", "counter-example and rejection conditions"),
]

TASKS = [
    ("extract", "Extract 5 concrete motifs with citation-backed hints."),
    ("compare", "Compare across at least 2 sources and explain differences."),
    ("table", "Return a concise table with motif, evidence, and caveat."),
    ("risk", "List over-interpretation risks and mitigation checks."),
    ("language", "Draft safe wording that stays [HYPO] and non-deterministic."),
]

MODES = [
    ("baseline", "Use concise neutral style."),
    ("counterfactual", "Include one counterfactual scenario and rejection condition."),
    ("evidence_first", "Prioritize source-grounded statements and cite uncertainty explicitly."),
    ("ops_ready", "Format output as checklist-ready bullets for monthly B-Track reporting."),
]


def build_queries(limit: int) -> list[dict]:
    queries: list[dict] = []
    i = 1
    for (lens_key, lens_desc), (theme_key, theme_desc), (task_key, task_inst), (mode_key, mode_inst) in product(
        LENSES, THEMES, TASKS, MODES
    ):
        qid = f"rq{i:04d}_{lens_key}_{theme_key}_{task_key}_{mode_key}"
        question = (
            f"[HYPO][NON-DETERMINISTIC] In this notebook context, analyze {theme_desc} using the {lens_desc}. "
            f"{task_inst} {mode_inst} Keep strict B-Track framing and do not imply A-track trading triggers."
        )
        queries.append(
            {
                "id": qid,
                "tags": ["relaxed", lens_key, theme_key, task_key, mode_key],
                "question": question,
            }
        )
        i += 1
        if limit > 0 and len(queries) >= limit:
            break
    return queries


def main() -> int:
    ap = argparse.ArgumentParser(description="Build relaxed large query pack for NotebookLM B-track.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--limit", type=int, default=300, help="Number of generated questions.")
    args = ap.parse_args()

    queries = build_queries(args.limit)
    payload = {
        "schema": "btrack_notebooklm_query_pack_relaxed_v1",
        "version": "1.0.0",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "a_track_autobind_forbidden": True,
        "label": "[HYPO] Relaxed high-volume comparative prompts (B-track only).",
        "query_count": len(queries),
        "queries": queries,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output} ({len(queries)} queries)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

