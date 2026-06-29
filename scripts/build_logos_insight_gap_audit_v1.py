#!/usr/bin/env python3
"""Insight gap audit — graph hop gaps + orphan citation risk [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.run_logos_llm_distill_citation_lock_v1 import VERSE_CITE_RE, _validate_citations

THEMES = ("dan_aramaic", "john_1_logos")
OUT_DEFAULT = ROOT / "reports/logos_insight_gap_audit_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _graph_adjacency(theme_id: str) -> dict[str, set[str]]:
    distill_path = ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
    doc = json.loads(distill_path.read_text(encoding="utf-8-sig"))
    adj: dict[str, set[str]] = {}
    for path in doc.get("graph_paths") or []:
        if not isinstance(path, dict):
            continue
        steps = [str(s) for s in (path.get("steps") or path.get("verse_ids") or []) if s]
        for i, a in enumerate(steps):
            adj.setdefault(a, set())
            for b in steps[i + 1 : i + 3]:
                adj[a].add(b)
                adj.setdefault(b, set()).add(a)
    return adj


def _hop_gap_pairs(anchors: list[str], adj: dict[str, set[str]]) -> list[dict[str, str]]:
    gaps: list[dict[str, str]] = []
    for i, a in enumerate(anchors):
        for b in anchors[i + 1 :]:
            if b in adj.get(a, set()) or a in adj.get(b, set()):
                continue
            shared = adj.get(a, set()) & adj.get(b, set())
            if not shared:
                gaps.append({"verse_a": a, "verse_b": b, "gap_type": "no_1hop_path"})
    return gaps[:30]


def audit_theme(theme_id: str) -> dict[str, Any]:
    distill_path = ROOT / f"docs/final/artifacts/logos_deep_research_distill_{theme_id}_citation_lock_latest.json"
    doc = json.loads(distill_path.read_text(encoding="utf-8-sig"))
    evidence = [r for r in (doc.get("evidence_refs") or []) if isinstance(r, dict)]
    anchors = [str(r["verse_id"]) for r in evidence if r.get("verse_id")]
    allowed = set(anchors)
    narr = (doc.get("distill_narrative_stub_ko") or {}).get("body_ko") or ""
    citation_check = _validate_citations(narr, allowed)
    adj = _graph_adjacency(theme_id)
    return {
        "theme_id": theme_id,
        "anchor_count": len(anchors),
        "graph_hop_gaps": _hop_gap_pairs(anchors[:16], adj),
        "narrative_citation_check": citation_check,
        "logic_leap_risk": len(citation_check.get("orphan_citations") or []) > 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    themes = [audit_theme(t) for t in THEMES]
    total_gaps = sum(len(t["graph_hop_gaps"]) for t in themes)
    doc = {
        "schema": "logos_insight_gap_audit_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "bible_ai_technique": "relink_path_repair_diagnostic",
        "themes": themes,
        "summary": {"hop_gap_pairs": total_gaps, "themes": len(themes)},
        "reproduce": "py scripts/build_logos_insight_gap_audit_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "hop_gaps": total_gaps, "out": str(args.out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
