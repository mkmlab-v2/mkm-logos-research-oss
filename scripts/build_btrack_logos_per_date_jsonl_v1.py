#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build B-track Logos per-date JSONL from macro gate causal-asof [HYPO][NON_GATING]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_logos_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_LOGOS_PER_DATE_JSONL,
    build_logos_per_date_rows,
)
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2026-01-01")
    ap.add_argument("--date-to", default="2026-06-08")
    ap.add_argument("--neutral-bps", type=float, default=5.0)
    ap.add_argument("--csv", type=Path, default=v1.KOSPI_CSV)
    ap.add_argument("--logos-lens", type=Path, default=DEFAULT_LOGOS_LENS)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_LOGOS_PER_DATE_JSONL)
    args = ap.parse_args()

    closes = v1._load_closes(args.csv)
    trading_days = sorted(closes.keys())
    rows, panel_meta = build_logos_per_date_rows(
        trading_days=trading_days,
        closes=closes,
        date_from=args.date_from,
        date_to=args.date_to,
        neutral_bps=args.neutral_bps,
        logos_lens=args.logos_lens,
    )

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in rows) + "\n",
        encoding="utf-8",
    )

    root_resolved = ROOT.resolve()
    meta = {
        "schema": "build_btrack_logos_per_date_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "non_gating": True,
        **panel_meta,
        "out_jsonl": str(args.out_jsonl.resolve().relative_to(root_resolved)).replace("\\", "/"),
        "note_ko": "성경(Logos) per-date macro gate — advisory only; Track A·실매매 트리거 아님.",
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
