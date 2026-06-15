#!/usr/bin/env python3
"""Check LTM graph JSON row counts vs NL brief SSOT — exit 1 on drift."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GRAPH = ROOT / "storage/meta/mkm_long_term_memory_graph_v1.json"
BRIEF = ROOT / "docs/final/NOTEBOOKLM_OPS_COMMAND_BRIEF_LTM_GRAPH_OS_V1.md"


def main() -> int:
    if not GRAPH.is_file():
        print(f"FAIL: missing graph: {GRAPH}", file=sys.stderr)
        return 1
    g = json.loads(GRAPH.read_text(encoding="utf-8"))
    concepts = len(g.get("concepts") or {})
    edges = len(g.get("edges") or [])
    if not BRIEF.is_file():
        print(f"FAIL: missing brief: {BRIEF}", file=sys.stderr)
        return 1
    text = BRIEF.read_text(encoding="utf-8")
    m_c = re.search(r"concepts\s*\|\s*\*\*(\d+)\*\*", text)
    m_e = re.search(r"edges\s*\|\s*\*\*(\d+)\*\*", text)
    errors: list[str] = []
    if not m_c or int(m_c.group(1)) != concepts:
        errors.append(f"brief concepts {m_c.group(1) if m_c else '?'} != graph {concepts}")
    if not m_e or int(m_e.group(1)) != edges:
        errors.append(f"brief edges {m_e.group(1) if m_e else '?'} != graph {edges}")
    if errors:
        for e in errors:
            print(f"FAIL: {e}", file=sys.stderr)
        return 1
    print(json.dumps({"ok": True, "concepts": concepts, "edges": edges, "brief": str(BRIEF.relative_to(ROOT))}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
