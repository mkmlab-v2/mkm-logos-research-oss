#!/usr/bin/env python3
"""Build triage outputs from accumulated NotebookLM B-track insights JSONL.

Outputs:
- top_motifs_top20: tag/motif frequency with source coverage
- high_confidence_top30: citation/source dense rows
- reject_candidates_top20: low-evidence or caution-heavy rows
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "notebooklm" / "btrack_mega_insights_10gb.jsonl"
DEFAULT_OUT = ROOT / "reports" / "notebooklm" / "btrack_insight_triage_latest.json"

WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z_\\-]{3,}")
STOP = {
    "with",
    "from",
    "that",
    "this",
    "have",
    "will",
    "into",
    "using",
    "should",
    "where",
    "when",
    "what",
    "which",
    "their",
    "there",
    "about",
    "only",
    "notebook",
    "track",
    "btrack",
    "hypo",
    "non",
    "deterministic",
    "medical",
}


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rows(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _evidence_score(row: dict[str, Any]) -> float:
    src = row.get("sources_used") or []
    cits = row.get("citations") or {}
    refs = row.get("references") or []
    ans = str(row.get("answer") or "")
    ln = len(ans)
    # favor citation/source density with modest length bonus
    return float(len(src) * 2 + len(cits) * 1.5 + len(refs) * 1.0 + min(ln, 4000) / 800.0)


def _risk_score(row: dict[str, Any]) -> float:
    ans = str(row.get("answer") or "").lower()
    src = row.get("sources_used") or []
    cits = row.get("citations") or {}
    refs = row.get("references") or []
    score = 0.0
    if len(src) == 0:
        score += 3.0
    if len(cits) == 0:
        score += 2.0
    if len(refs) == 0:
        score += 1.0
    # caution-heavy phrasing can indicate generic/non-actionable outputs
    for kw in ("cannot", "unable", "not available", "insufficient", "no data"):
        if kw in ans:
            score += 1.0
    score += max(0.0, 1.5 - len(ans) / 600.0)  # very short answer penalty
    return score


def _motifs(rows: list[dict[str, Any]], top_n: int) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    source_coverage: dict[str, set[str]] = {}

    for r in rows:
        tags = [str(t).lower() for t in (r.get("tags") or [])]
        for t in tags:
            if t and t not in STOP:
                counts[t] += 1
                source_coverage.setdefault(t, set()).update(str(s) for s in (r.get("sources_used") or []))
        ans = str(r.get("answer") or "").lower()
        for w in WORD_RE.findall(ans):
            w = w.lower()
            if w in STOP:
                continue
            counts[w] += 1

    out = []
    for k, v in counts.most_common(top_n):
        out.append(
            {
                "motif": k,
                "count": int(v),
                "source_coverage": len(source_coverage.get(k, set())),
            }
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build triage set from B-track mega insights JSONL.")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--motif-top", type=int, default=20)
    ap.add_argument("--high-top", type=int, default=30)
    ap.add_argument("--reject-top", type=int, default=20)
    args = ap.parse_args()

    if not args.input_jsonl.is_file():
        raise SystemExit(f"missing input jsonl: {args.input_jsonl}")

    rows = _rows(args.input_jsonl)
    if not rows:
        raise SystemExit("no valid rows in input")

    enriched = []
    for r in rows:
        enriched.append(
            {
                "query_id": r.get("query_id"),
                "tags": r.get("tags") or [],
                "conversation_id": r.get("conversation_id"),
                "sources_used_count": len(r.get("sources_used") or []),
                "citations_count": len((r.get("citations") or {})),
                "references_count": len(r.get("references") or []),
                "answer_preview": str(r.get("answer") or "")[:400],
                "evidence_score": round(_evidence_score(r), 4),
                "risk_score": round(_risk_score(r), 4),
            }
        )

    high = sorted(enriched, key=lambda x: x["evidence_score"], reverse=True)[: args.high_top]
    reject = sorted(enriched, key=lambda x: x["risk_score"], reverse=True)[: args.reject_top]
    motifs = _motifs(rows, args.motif_top)

    payload = {
        "schema": "btrack_insight_triage_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "a_track_autobind_forbidden": True,
        "label": "[HYPO] Triage set from accumulated NotebookLM insights.",
        "input_jsonl": str(args.input_jsonl),
        "rows_total": len(rows),
        "top_motifs_top20": motifs,
        "high_confidence_top30": high,
        "reject_candidates_top20": reject,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output} rows_total={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

