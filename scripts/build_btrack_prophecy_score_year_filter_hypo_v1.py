#!/usr/bin/env python3
"""Filter btrack_prophecy_score rows by year/instrument to reports copy (B-track, no prod write)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "reports/btrack_prophecy_score_hybrid_session_kospi_252d_v1.json"
DEFAULT_OUT = ROOT / "reports/btrack_prophecy_score_kospi_2025_nonstress_hypo_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-json", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--year-from", type=int, default=2025)
    ap.add_argument("--year-to", type=int, default=2025)
    ap.add_argument("--instrument", default="kospi")
    args = ap.parse_args()

    src = args.input_json if args.input_json.is_absolute() else ROOT / args.input_json
    doc: dict[str, Any] = json.loads(src.read_text(encoding="utf-8-sig"))
    inst = str(args.instrument).strip().lower()
    kept = []
    for r in doc.get("rows", []):
        if not isinstance(r, dict):
            continue
        if str(r.get("instrument") or "").strip().lower() != inst:
            continue
        ed = str(r.get("eval_date") or "")[:10]
        if len(ed) < 4:
            continue
        yr = int(ed[:4])
        if yr < args.year_from or yr > args.year_to:
            continue
        kept.append(r)

    out_doc = {
        **{k: v for k, v in doc.items() if k != "rows"},
        "rows": kept,
        "filter_meta": {
            "source": str(src.relative_to(ROOT)).replace("\\", "/"),
            "generated_at_utc": _utc_now(),
            "year_from": args.year_from,
            "year_to": args.year_to,
            "instrument": inst,
            "n_rows": len(kept),
            "research_only": True,
            "hypothesis_tag": "[HYPO]",
        },
    }
    out_path = args.output if args.output.is_absolute() else ROOT / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out_path} n_rows={len(kept)}")
    return 0 if kept else 1


if __name__ == "__main__":
    raise SystemExit(main())
