#!/usr/bin/env python3
"""Build recommendation pack from btrack_insight_triage_latest.json.

Outputs:
- final_high_confidence_top10 (deduped by query_id)
- reject_reason_table (top20 with human-readable reason labels)
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "notebooklm" / "btrack_insight_triage_latest.json"
DEFAULT_OUT = ROOT / "reports" / "notebooklm" / "btrack_insight_recommendation_pack_latest.json"
DEFAULT_MD = ROOT / "reports" / "notebooklm" / "btrack_reject_reason_table_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _reason(item: dict[str, Any]) -> str:
    src = int(item.get("sources_used_count") or 0)
    cit = int(item.get("citations_count") or 0)
    ref = int(item.get("references_count") or 0)
    risk = float(item.get("risk_score") or 0.0)
    reasons: list[str] = []
    if src == 0:
        reasons.append("no_sources")
    if cit == 0:
        reasons.append("no_citations")
    if ref == 0:
        reasons.append("no_references")
    if risk >= 3:
        reasons.append("high_risk_score")
    if len(str(item.get("answer_preview") or "")) < 120:
        reasons.append("too_short")
    return ",".join(reasons) if reasons else "low_actionability_or_redundancy"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build recommendation pack from btrack triage JSON.")
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--reject-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--top-n", type=int, default=10)
    args = ap.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"missing input: {args.input}")
    triage = json.loads(args.input.read_text(encoding="utf-8"))
    high = [x for x in triage.get("high_confidence_top30", []) if isinstance(x, dict)]
    reject = [x for x in triage.get("reject_candidates_top20", []) if isinstance(x, dict)]

    seen: set[str] = set()
    final10: list[dict[str, Any]] = []
    for item in high:
        qid = str(item.get("query_id") or "")
        if not qid or qid in seen:
            continue
        seen.add(qid)
        final10.append(item)
        if len(final10) >= args.top_n:
            break

    reject_rows: list[dict[str, Any]] = []
    for item in reject[:20]:
        reject_rows.append(
            {
                "query_id": item.get("query_id"),
                "risk_score": item.get("risk_score"),
                "sources_used_count": item.get("sources_used_count"),
                "citations_count": item.get("citations_count"),
                "references_count": item.get("references_count"),
                "reject_reason": _reason(item),
                "answer_preview": str(item.get("answer_preview") or "")[:240],
            }
        )

    payload = {
        "schema": "btrack_insight_recommendation_pack_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "a_track_autobind_forbidden": True,
        "label": "[HYPO] Recommendation pack from triage outputs.",
        "input_triage": str(args.input),
        "final_high_confidence_top10": final10,
        "reject_reason_table": reject_rows,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# B-Track Reject Reason Table (Top20)",
        "",
        "| query_id | risk_score | src/cit/ref | reject_reason |",
        "|---|---:|---:|---|",
    ]
    for r in reject_rows:
        md_lines.append(
            f"| `{r['query_id']}` | {r['risk_score']} | {r['sources_used_count']}/{r['citations_count']}/{r['references_count']} | `{r['reject_reason']}` |"
        )
    args.reject_md.parent.mkdir(parents=True, exist_ok=True)
    args.reject_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")

    print(f"WROTE: {args.output}")
    print(f"WROTE: {args.reject_md}")
    print(f"final_high_confidence_top10={len(final10)} reject_rows={len(reject_rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

