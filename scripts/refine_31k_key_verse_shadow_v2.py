#!/usr/bin/env python3
"""Refine 31k key-verse shadow post-its with stronger evidence/confidence rules."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "reports/verse_metadata_shadow_v1_latest.json"
OUT_DEFAULT = ROOT / "reports/verse_metadata_shadow_v2_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (json.JSONDecodeError, OSError):
        return {}


def build(*, min_confidence: float, min_citation_hits: int, top_n: int) -> dict[str, Any]:
    src = _load(SRC)
    rows = []
    for row in (src.get("rows") or []):
        conf = float(row.get("confidence") or 0.0)
        hits = int(((row.get("evidence") or {}).get("citation_hit_count")) or 0)
        if conf < min_confidence or hits < min_citation_hits:
            continue
        row2 = dict(row)
        row2["quality_flags"] = {
            "min_confidence_ok": conf >= min_confidence,
            "min_citation_hits_ok": hits >= min_citation_hits,
            "evidence_complete": bool((row.get("evidence") or {}).get("source_units")),
        }
        row2["non_gating"] = True
        row2["research_only"] = True
        rows.append(row2)
        if top_n and len(rows) >= top_n:
            break
    return {
        "schema": "verse_metadata_shadow_v2",
        "version": "2.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "inputs": {
            "source_shadow_v1": str(SRC.relative_to(ROOT)).replace("\\", "/"),
            "min_confidence": min_confidence,
            "min_citation_hits": min_citation_hits,
            "top_n": top_n,
        },
        "summary": {
            "source_rows": len(src.get("rows") or []),
            "rows": len(rows),
        },
        "rows": rows,
        "reproduce": "py scripts/refine_31k_key_verse_shadow_v2.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--min-confidence", type=float, default=0.7)
    ap.add_argument("--min-citation-hits", type=int, default=1)
    ap.add_argument("--top-n", type=int, default=256)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()
    doc = build(
        min_confidence=max(0.0, min(1.0, args.min_confidence)),
        min_citation_hits=max(1, args.min_citation_hits),
        top_n=max(1, args.top_n),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ok = int((doc.get("summary") or {}).get("rows") or 0) > 0
    print(json.dumps({"ok": ok, "rows": doc["summary"]["rows"], "out": str(args.out)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
