#!/usr/bin/env python3
"""[HYPO] B-track myeongni per-date JSONL from manseryeok session wall-clock (science_core lane).

Deterministic KRX session 09:00 Asia/Seoul → mapping_target + state_id. Not personal birth chart.
research_only — do not merge to Track A / live trading.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_myeongni_jsonl_from_manseryeok_session_v1 import (  # noqa: E402
    build_myeongni_session_jsonl_rows,
)

DEFAULT_OUT = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2026-01-01")
    ap.add_argument("--date-to", default="2026-06-08")
    ap.add_argument("--calendar-mode", default="krx_weekdays", choices=("all", "krx_weekdays"))
    ap.add_argument("--neutral-band", type=float, default=0.06)
    ap.add_argument("--out-jsonl", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    my_lines, _, panel_meta = build_myeongni_session_jsonl_rows(
        date_from=args.date_from,
        date_to=args.date_to,
        calendar_mode=args.calendar_mode,
        neutral_band=args.neutral_band,
    )

    args.out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    args.out_jsonl.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in my_lines) + "\n",
        encoding="utf-8",
    )

    root_resolved = ROOT.resolve()
    meta = {
        "schema": "btrack_myeongni_per_date_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "stub": False,
        "source_provenance": "manseryeok_session_per_date_v1",
        **panel_meta,
        "out_jsonl": str(args.out_jsonl.resolve().relative_to(root_resolved)).replace("\\", "/"),
        "note_ko": "Science Core humanist leg — session manseryeok only; not 擇日/日課.",
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
