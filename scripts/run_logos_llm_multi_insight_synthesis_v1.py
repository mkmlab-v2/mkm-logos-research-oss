#!/usr/bin/env python3
"""Multi-insight Ollama synthesis — cross-theme + paper-guided units [HYPO]."""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_logos_llm_distill_citation_lock_v1 import _validate_citations, try_ollama_distill_narrative

OUT_DEFAULT = ROOT / "reports/logos_multi_insight_synthesis_v1_latest.json"
REFS_PATH = ROOT / "docs/final/artifacts/logos_bible_ai_research_refs_v1.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _evidence_merged() -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for theme in ("dan_aramaic", "john_1_logos"):
        doc = _load(ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme}_citation_lock_latest.json")
        for r in doc.get("evidence_refs") or []:
            if isinstance(r, dict) and r.get("verse_id"):
                refs.append(r)
    return refs


def _insight_prompt(kind: str, bridge: dict[str, Any], refs: list[dict[str, Any]]) -> str:
    hubs = (bridge.get("shared_hubs") or [])[:3]
    inv = (bridge.get("semantic_invariants") or [])[:3]
    hub_txt = ", ".join(h["hub_verse_id"] for h in hubs if h.get("hub_verse_id"))
    inv_txt = ", ".join(i["invariant_id"] for i in inv if i.get("invariant_id"))
    return (
        f"[TRACK B / HYPO / NON_GATING] Insight kind={kind}. "
        f"Use Relink-style query-specific evidence paths; cite ONLY allowed verse_ids. "
        f"Shared xref hubs: {hub_txt or 'none'}. Invariants: {inv_txt or 'none'}. "
        "No doctrine marketing; no B2B sales copy; 2 short paragraphs with [HYPO] prefix."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--max-units", type=int, default=8)
    ap.add_argument("--skip-ollama", action="store_true")
    args = ap.parse_args()

    bridge_path = ROOT / "reports/logos_cross_theme_invariant_bridge_v1_latest.json"
    bridge = _load(bridge_path) if bridge_path.is_file() else {}
    refs = _evidence_merged()
    allowed = {str(r["verse_id"]) for r in refs if r.get("verse_id")}

    kinds = [
        "cross_theme_authority",
        "cross_theme_revelation",
        "path_alignment_hub",
        "dialectical_synthesis_bridge",
        "graph_gap_repair_hypothesis",
        "scripture_alignment_layer",
        "query_driven_evidence_path",
        "invariant_order_logos",
    ][: max(1, args.max_units)]

    units: list[dict[str, Any]] = []
    llm_ok = False
    if not args.skip_ollama and os.environ.get("MKM_LOGOS_LLM_DISTILL_ENABLE", "").strip().lower() in {"1", "true", "yes", "on"}:
        host = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/").replace("/v1", "")
        model = os.getenv("OLLAMA_MODEL", "gemma4:e2b")
        for kind in kinds:
            narr = try_ollama_distill_narrative(
                refs[:10],
                theme_title=_insight_prompt(kind, bridge, refs),
                host=host,
                model=model,
                timeout=180,
            )
            if not narr or not narr.get("body_ko"):
                continue
            validation = _validate_citations(str(narr["body_ko"]), allowed)
            units.append(
                {
                    "insight_id": kind,
                    "body_ko": narr["body_ko"],
                    "llm_invoked": True,
                    **validation,
                }
            )
        llm_ok = len(units) > 0

    if not units:
        for kind in kinds:
            units.append(
                {
                    "insight_id": kind,
                    "body_ko": f"[HYPO] {kind} — stub insight unit; enable Ollama for expanded synthesis.",
                    "llm_invoked": False,
                    "citation_valid": True,
                    "orphan_citations": [],
                }
            )

    refs_doc = _load(REFS_PATH) if REFS_PATH.is_file() else {"refs": []}
    doc = {
        "schema": "logos_multi_insight_synthesis_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "llm_batch_ok": llm_ok,
        "bible_ai_refs_applied": [r.get("ref_id") for r in (refs_doc.get("refs") or [])[:6]],
        "insight_units": units,
        "summary": {"unit_count": len(units), "llm_units": sum(1 for u in units if u.get("llm_invoked"))},
        "reproduce": "py scripts/run_logos_llm_multi_insight_synthesis_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "units": len(units), "llm": llm_ok, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
