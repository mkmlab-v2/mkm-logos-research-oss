#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Science Core news component coverage audit [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_science_core_v1 import build_news_by_published_day, news_lens_at_date  # noqa: E402

DEFAULT_OUT = ROOT / "reports/science_core_news_coverage_audit_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_news_coverage_audit_v1_latest.json"
DEFAULT_EXA = ROOT / "reports/exa_macro_news_observation_staging_v1_latest.jsonl"
DEFAULT_SCIENCE = ROOT / "reports/btrack_science_core_per_date_kospi_v1.jsonl"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows


def run_audit(
    *,
    science_jsonl: Path,
    exa_jsonl: Path,
    date_from: str | None,
    date_to: str | None,
    lookback_calendar_days: int = 14,
) -> dict[str, Any]:
    science_rows = _read_jsonl(science_jsonl)
    if date_from:
        science_rows = [r for r in science_rows if str(r.get("session_date") or "")[:10] >= date_from]
    if date_to:
        science_rows = [r for r in science_rows if str(r.get("session_date") or "")[:10] <= date_to]

    stored_modes = Counter()
    for row in science_rows:
        news = (row.get("components") or {}).get("news") or {}
        stored_modes[str(news.get("mode") or "missing")] += 1

    news_by_day = build_news_by_published_day(exa_jsonl)
    exa_published_days = sorted(news_by_day.keys())
    simulated_modes = Counter()
    for row in science_rows:
        dk = str(row.get("session_date") or "")[:10]
        if len(dk) != 10:
            continue
        _, _, meta = news_lens_at_date(
            news_by_day,
            dk,
            lookback_calendar_days=lookback_calendar_days,
        )
        simulated_modes[str(meta.get("mode") or "missing")] += 1

    n = len(science_rows) or 1
    causal_sim = int(simulated_modes.get("causal_exa_news_window", 0))
    causal_stored = int(stored_modes.get("causal_exa_news_window", 0))
    return {
        "schema": "science_core_news_coverage_audit_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "window": {"from": date_from, "to": date_to},
        "science_jsonl": str(science_jsonl),
        "exa_jsonl": str(exa_jsonl),
        "n_science_rows": len(science_rows),
        "exa_unique_published_days": len(exa_published_days),
        "exa_published_day_range": [exa_published_days[0], exa_published_days[-1]] if exa_published_days else None,
        "lookback_calendar_days": lookback_calendar_days,
        "stored_news_modes": dict(stored_modes),
        "simulated_news_modes": dict(simulated_modes),
        "causal_exa_share_stored": round(causal_stored / n, 4),
        "causal_exa_share_simulated": round(causal_sim / n, 4),
        "sparse_causal_coverage": causal_sim < max(10, int(n * 0.05)),
        "note_ko": (
            "simulated_*는 현재 EXA staging으로 news_lens_at_date 재계산. "
            "science JSONL rebuild 전이면 stored와 simulated가 다를 수 있음."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--science-jsonl", type=Path, default=DEFAULT_SCIENCE)
    ap.add_argument("--exa-jsonl", type=Path, default=DEFAULT_EXA)
    ap.add_argument("--date-from", type=str, default=None)
    ap.add_argument("--date-to", type=str, default=None)
    ap.add_argument("--lookback-calendar-days", type=int, default=14)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    doc = run_audit(
        science_jsonl=args.science_jsonl,
        exa_jsonl=args.exa_jsonl,
        date_from=args.date_from,
        date_to=args.date_to,
        lookback_calendar_days=max(1, int(args.lookback_calendar_days)),
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} causal_simulated={doc['causal_exa_share_simulated']} "
        f"exa_days={doc['exa_unique_published_days']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
