#!/usr/bin/env python3
"""Join bench input raw text with active report reconstructions; emit token loss patterns."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.report_multilens_performance_eval import _norm_words

INPUT_V2 = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_PERFORMANCE_EVAL_INPUT_V2.json"
ACTIVE_DEFAULT = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json"
ACTIVE_LITERAL = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_LITERAL_V1.json"
ACTIVE_ULTRA_LITERAL = ROOT / "docs" / "final" / "artifacts" / "MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_ULTRA_LITERAL_V1.json"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_jaccard_loss_patterns_latest.json"
OUT_LITERAL = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_jaccard_loss_patterns_literal_latest.json"
OUT_ULTRA_LITERAL = ROOT / "reports" / "constitution" / "btrack_pilot" / "compression_jaccard_loss_patterns_ultra_literal_latest.json"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Jaccard-oriented token loss patterns (raw vs reconstructed).")
    p.add_argument("--input", default=str(INPUT_V2), help="Bench input JSON with raw_text per case id")
    p.add_argument(
        "--sla-track",
        choices=("universal", "literal", "ultra_literal"),
        default="universal",
        help="Select active report + output: universal (ops), literal (Track B), or ultra_literal (research).",
    )
    p.add_argument(
        "--active-report",
        default=None,
        help="Override active multilens report path (default: from --sla-track).",
    )
    p.add_argument("--output", default=None, help="Output JSON path (default: from --sla-track).")
    return p


def main() -> int:
    args = _parser().parse_args()
    inp_path = Path(args.input)
    active_path = Path(args.active_report) if args.active_report else (
        ACTIVE_ULTRA_LITERAL
        if args.sla_track == "ultra_literal"
        else (ACTIVE_LITERAL if args.sla_track == "literal" else ACTIVE_DEFAULT)
    )
    out_path = Path(args.output) if args.output else (
        OUT_ULTRA_LITERAL
        if args.sla_track == "ultra_literal"
        else (OUT_LITERAL if args.sla_track == "literal" else OUT)
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)

    src = json.loads(inp_path.read_text(encoding="utf-8"))
    active = json.loads(active_path.read_text(encoding="utf-8"))
    raw_by_id = {str(c.get("id")): str(c.get("raw_text", "")) for c in src.get("compression_cases", [])}
    cases = (active.get("compression_metrics") or {}).get("cases") or []

    rows: list[dict[str, Any]] = []
    for row in cases:
        cid = str(row.get("id", ""))
        raw = raw_by_id.get(cid, "")
        rec = str(row.get("reconstructed_text_effective", ""))
        rw = _norm_words(raw)
        rr = _norm_words(rec)
        lost = sorted(rw - rr)
        extra = sorted(rr - rw)
        route = row.get("route") if isinstance(row.get("route"), dict) else {}
        rows.append(
            {
                "id": cid,
                "domain": route.get("domain"),
                "shard_id": route.get("shard_id"),
                "reconstruction_fidelity_jaccard": row.get("reconstruction_fidelity_jaccard"),
                "token_saving_rate": row.get("token_saving_rate"),
                "raw_word_count": len(rw),
                "recon_word_count": len(rr),
                "words_lost_count": len(lost),
                "words_extra_count": len(extra),
                "words_lost_sample": lost[:40],
                "words_extra_sample": extra[:40],
            }
        )

    def _rel(p: Path) -> str:
        try:
            return str(p.relative_to(ROOT))
        except ValueError:
            return str(p)

    doc = {
        "schema": "compression_jaccard_loss_patterns_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "sla_track": args.sla_track,
        "sources": {
            "input": _rel(inp_path),
            "active_report": _rel(active_path),
        },
        "summary": {
            "case_count": len(rows),
            "avg_words_lost": (sum(r["words_lost_count"] for r in rows) / len(rows)) if rows else 0.0,
        },
        "cases": rows,
    }
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
