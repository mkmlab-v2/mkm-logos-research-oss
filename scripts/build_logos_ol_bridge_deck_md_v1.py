#!/usr/bin/env python3
"""Build internal OL GraphRAG bridge deck Markdown (print/PDF paste · [HYPO] · NON_GATING)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ALIGNMENT = ROOT / "reports/logos_ol_graph_bridge_alignment_v1_latest.json"
PHASE3_CHAIN = ROOT / "reports/logos_ol_graph_bridge_phase3_chain_v1_latest.json"
BRIDGE_DOC = ROOT / "docs/final/LOGOS_ORIGINAL_LANGUAGE_GRAPH_RAG_BRIDGE_V1.md"
DEFAULT_OUT = ROOT / "reports/logos_ops_deck/logos_ol_bridge_deck_v1.md"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return doc if isinstance(doc, dict) else {}


def build(*, alignment: dict[str, Any], phase3_chain: dict[str, Any]) -> str:
    gaps = alignment.get("phase_gaps") or []
    lines = [
        "# Logos OL GraphRAG Bridge — Internal Deck v1",
        "",
        f"- generated_at_utc: `{_utc()}`",
        "- evidence_tier: `[HYPO]` · `research_only` · `NON_GATING`",
        "- send_gate: `HOLD` — not Track A · not live trading · not prophecy hit-rate",
        "",
        "## Phase closure (local Fact-Lock)",
        "",
        f"| Phase | complete |",
        f"|-------|----------|",
        f"| 0 static bridge + wire PoC | `{alignment.get('phase0_complete')}` |",
        f"| 1 lemma↔verse edges + corpus split | `{alignment.get('phase1_complete')}` |",
        f"| 2 concept_bridge LLM + human_review | `{alignment.get('phase2_complete')}` |",
        f"| 3 subgraph router + showroom audit | `{alignment.get('phase3_complete')}` |",
        "",
        "## Headline metrics",
        "",
        f"- lemma_edge_count: `{alignment.get('lemma_edge_count')}`",
        f"- corpus_split_gate_pass: `{alignment.get('corpus_split_gate_pass')}`",
        f"- concept_bridge_count: `{alignment.get('concept_bridge_registry_count')}`",
        f"- human_reviewed_ratio: `{alignment.get('concept_bridge_human_reviewed_ratio')}`",
        f"- llm_bridge_count: `{alignment.get('concept_bridge_llm_bridge_count')}`",
        f"- subgraph_replay_pass_count: `{alignment.get('subgraph_replay_pass_count')}`",
        f"- showroom_audit_slice_gate_pass: `{alignment.get('showroom_audit_slice_gate_pass')}`",
        f"- phase3_chain_ok: `{phase3_chain.get('ok')}`",
        "",
        "## Remaining gaps",
        "",
    ]
    if gaps:
        for g in gaps:
            lines.append(f"- {g}")
    else:
        lines.append("- (none)")
    lines.extend(
        [
            "",
            "## Human deck checklist (before external paste)",
            "",
            "1. Confirm no prophecy / era-blind 4.3% substitution claims.",
            "2. Confirm lemma labels are educational anchors, not morphology proof.",
            "3. Confirm showroom v6 audit panel shows `[HYPO]` + `NON_GATING`.",
            "4. Commander sign-off on PDF export path below.",
            "",
            "## SSOT & reproduce",
            "",
            f"- bridge doc: `{BRIDGE_DOC.relative_to(ROOT).as_posix()}`",
            "- `py scripts/run_logos_ol_graph_bridge_phase1_chain_v1.py`",
            "- `py scripts/run_logos_ol_graph_bridge_phase2_chain_v1.py`",
            "- `py scripts/run_logos_ol_graph_bridge_phase3_chain_v1.py`",
            "- `py scripts/run_logos_ol_graph_bridge_post_phase3_closure_v1.py`",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--alignment-json", type=Path, default=ALIGNMENT)
    ap.add_argument("--phase3-chain-json", type=Path, default=PHASE3_CHAIN)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    alignment = _read(args.alignment_json)
    if not alignment:
        print(f"missing alignment: {args.alignment_json}", file=__import__("sys").stderr)
        return 2

    text = build(alignment=alignment, phase3_chain=_read(args.phase3_chain_json))
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(text, encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_md)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
