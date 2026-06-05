#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Roll up June KOSPI shadow panel JSONL into forward soft trend [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_LOG = ROOT / "reports/kospi_june2026_shadow_panel_log.jsonl"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_shadow_panel_rollup_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(doc, dict):
            rows.append(doc)
    return rows


def build_rollup(
    *,
    log_path: Path,
    year_month: str = "2026-06",
    lookback_entries: int | None = None,
) -> dict[str, Any]:
    entries = _read_jsonl(log_path)
    if lookback_entries is not None and lookback_entries > 0:
        entries = entries[-lookback_entries:]

    series: list[dict[str, Any]] = []
    for entry in entries:
        shadows_out: list[dict[str, Any]] = []
        for s in entry.get("shadows") or []:
            if not isinstance(s, dict):
                continue
            shadows_out.append(
                {
                    "candidate_id": s.get("candidate_id"),
                    "soft_hit_rate": s.get("soft_hit_rate"),
                    "soft_delta_vs_active": s.get("soft_delta_vs_active"),
                    "n_calendar_direction_diffs": s.get("n_calendar_direction_diffs"),
                }
            )
        series.append(
            {
                "session_date_kst": entry.get("session_date_kst"),
                "logged_at_utc": entry.get("logged_at_utc"),
                "active_n_scored": entry.get("active_n_scored"),
                "active_soft_hit_rate": entry.get("active_soft_hit_rate"),
                "applied_active_id": entry.get("applied_active_id"),
                "shadows": shadows_out,
            }
        )

    first = series[0] if series else None
    last = series[-1] if series else None
    delta_n_scored: int | None = None
    delta_active_soft: float | None = None
    if first and last:
        f_n = first.get("active_n_scored")
        l_n = last.get("active_n_scored")
        if f_n is not None and l_n is not None:
            delta_n_scored = int(l_n) - int(f_n)
        f_s = first.get("active_soft_hit_rate")
        l_s = last.get("active_soft_hit_rate")
        if f_s is not None and l_s is not None:
            delta_active_soft = round(float(l_s) - float(f_s), 6)

    leader_last: dict[str, Any] | None = None
    if last:
        candidates: list[dict[str, Any]] = [
            {
                "candidate_id": last.get("applied_active_id"),
                "role": "applied_active",
                "soft_hit_rate": last.get("active_soft_hit_rate"),
            }
        ]
        for s in last.get("shadows") or []:
            candidates.append(
                {
                    "candidate_id": s.get("candidate_id"),
                    "role": "research_shadow",
                    "soft_hit_rate": s.get("soft_hit_rate"),
                    "soft_delta_vs_active": s.get("soft_delta_vs_active"),
                }
            )
        scored = [c for c in candidates if c.get("soft_hit_rate") is not None]
        if scored:
            leader_last = max(scored, key=lambda x: float(x.get("soft_hit_rate") or -1))

    try:
        log_path_rel = str(log_path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        log_path_rel = str(log_path).replace("\\", "/")

    return {
        "schema": "kospi_june2026_shadow_panel_rollup_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "year_month": year_month,
        "log_path": log_path_rel,
        "n_log_entries": len(entries),
        "lookback_entries": lookback_entries,
        "series": series,
        "delta_first_to_last": {
            "active_n_scored": delta_n_scored,
            "active_soft_hit_rate": delta_active_soft,
            "first_session_date_kst": (first or {}).get("session_date_kst"),
            "last_session_date_kst": (last or {}).get("session_date_kst"),
        },
        "leader_by_last_forward_soft": leader_last,
        "note_ko": "shadow_panel_log 누적 추이 — apply·Track A·실매매 자동 합선 금지.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--log-jsonl", type=Path, default=DEFAULT_LOG)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--year-month", type=str, default="2026-06")
    ap.add_argument("--lookback-entries", type=int, default=None)
    args = ap.parse_args(argv)

    doc = build_rollup(
        log_path=args.log_jsonl,
        year_month=args.year_month,
        lookback_entries=args.lookback_entries,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} entries={doc['n_log_entries']} "
        f"leader={((doc.get('leader_by_last_forward_soft') or {}).get('candidate_id'))}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
