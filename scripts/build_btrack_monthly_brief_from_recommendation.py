#!/usr/bin/env python3
"""Build one-page monthly brief from btrack insight recommendation pack."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports" / "notebooklm" / "btrack_insight_recommendation_pack_latest.json"
DEFAULT_MD = ROOT / "docs" / "final" / "artifacts" / "btrack_monthly_brief_from_top10_latest.md"
DEFAULT_JSON = ROOT / "docs" / "final" / "artifacts" / "btrack_monthly_brief_from_top10_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _item_line(item: dict[str, Any], idx: int) -> str:
    qid = str(item.get("query_id") or f"item_{idx}")
    tags = ", ".join(str(t) for t in (item.get("tags") or [])[:5])
    es = item.get("evidence_score")
    rs = item.get("risk_score")
    prev = str(item.get("answer_preview") or "").replace("\n", " ").strip()
    prev = (prev[:180] + "...") if len(prev) > 180 else prev
    return f"{idx}. `{qid}` | evidence={es}, risk={rs} | tags={tags}\n   - {prev}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one-page B-track monthly brief from top10 recommendation pack.")
    ap.add_argument("--input", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_JSON)
    ap.add_argument(
        "--write-monthly-snapshot",
        action="store_true",
        help="Also write month-stamped copies (YYYY-MM) next to latest files.",
    )
    ap.add_argument(
        "--snapshot-month",
        default="",
        help="Optional snapshot month in YYYY-MM. Defaults to generated_at_utc month.",
    )
    args = ap.parse_args()

    if not args.input.is_file():
        raise SystemExit(f"missing input: {args.input}")
    doc = json.loads(args.input.read_text(encoding="utf-8"))
    top10 = [x for x in doc.get("final_high_confidence_top10", []) if isinstance(x, dict)]
    reject = [x for x in doc.get("reject_reason_table", []) if isinstance(x, dict)]

    top10_lines = [_item_line(it, i + 1) for i, it in enumerate(top10)]
    reject_lines = []
    for i, r in enumerate(reject[:10], start=1):
        reject_lines.append(
            f"{i}. `{r.get('query_id')}` | reason=`{r.get('reject_reason')}` | risk={r.get('risk_score')} "
            f"| src/cit/ref={r.get('sources_used_count')}/{r.get('citations_count')}/{r.get('references_count')}"
        )

    brief_json = {
        "schema": "btrack_monthly_brief_from_top10_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "research_only": True,
        "a_track_autobind_forbidden": True,
        "label": "[HYPO] One-page monthly brief from recommendation top10.",
        "source_recommendation_pack": str(args.input),
        "selected_top10_count": len(top10),
        "reject_sample_count": min(len(reject), 10),
        "selected_top10": top10,
        "reject_sample_top10": reject[:10],
        "operations_note": "B-track observation only. Promotion requires explicit gate and separate code-path evidence.",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(brief_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# B-Track Monthly Brief (Top10-Based)",
        "",
        f"- generated_at_utc: `{brief_json['generated_at_utc']}`",
        "- classification: `[HYPO]`, `research_only`, `a_track_autobind_forbidden`",
        f"- source: `{args.input}`",
        "",
        "## 1) Selected High-Confidence Top10",
        "",
        *top10_lines,
        "",
        "## 2) Reject/Defer Sample (Top10)",
        "",
        *reject_lines,
        "",
        "## 3) Actionable Operations",
        "",
        "- Keep selected Top10 in B-track observation queue only.",
        "- Defer reject candidates until source/citation density is improved or redundancy is removed.",
        "- Separate `proxy` vs `price` metrics in all reporting tables.",
        "- Any A-track consideration requires explicit promotion gate and code-path verification.",
        "",
    ]
    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    md_text = "\n".join(md)
    args.output_md.write_text(md_text, encoding="utf-8")
    print(f"WROTE: {args.output_md}")
    print(f"WROTE: {args.output_json}")

    if args.write_monthly_snapshot:
        month = args.snapshot_month.strip() or str(brief_json["generated_at_utc"])[:7]
        if len(month) != 7 or month[4] != "-":
            raise SystemExit(f"invalid --snapshot-month (expected YYYY-MM): {month}")
        md_snap = args.output_md.with_name(f"btrack_monthly_brief_from_top10_{month}.md")
        json_snap = args.output_json.with_name(f"btrack_monthly_brief_from_top10_{month}.json")
        md_snap.write_text(md_text, encoding="utf-8")
        json_snap.write_text(json.dumps(brief_json, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"WROTE: {md_snap}")
        print(f"WROTE: {json_snap}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

