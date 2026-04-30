#!/usr/bin/env python3
"""Weekly rebuild for agent memory: TTL cooling + hot promotion + compact summary."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_MEMORY_JSONL = ART / "agent_memory_deltas_v1.jsonl"
DEFAULT_HOT_JSONL = ART / "agent_memory_hot_v1.jsonl"
DEFAULT_SUMMARY = ART / "agent_memory_weekly_rebuild_summary_latest.json"
DEFAULT_COMPACT = ART / "agent_memory_compact_20_latest.json"
DEFAULT_MEMORY_A = ART / "agent_memory_deltas_track_a_v1.jsonl"
DEFAULT_MEMORY_B = ART / "agent_memory_deltas_track_b_v1.jsonl"
DEFAULT_COMBINED_MIRROR = ART / "agent_memory_deltas_v1.jsonl"


def _iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_utc(ts: str) -> datetime | None:
    s = str(ts or "").strip()
    if not s:
        return None
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    with path.open("r", encoding="utf-8-sig") as fh:
        for line in fh:
            s = line.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--memory-jsonl", type=Path, default=DEFAULT_MEMORY_JSONL)
    ap.add_argument("--memory-jsonl-a", type=Path, default=DEFAULT_MEMORY_A)
    ap.add_argument("--memory-jsonl-b", type=Path, default=DEFAULT_MEMORY_B)
    ap.add_argument("--combined-mirror-jsonl", type=Path, default=DEFAULT_COMBINED_MIRROR)
    ap.add_argument("--hot-jsonl", type=Path, default=DEFAULT_HOT_JSONL)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    ap.add_argument("--compact-json", type=Path, default=DEFAULT_COMPACT)
    ap.add_argument("--ttl-days", type=int, default=7)
    ap.add_argument("--compact-limit", type=int, default=20)
    ap.add_argument("--min-repro-score", type=int, default=1)
    args = ap.parse_args()

    now = datetime.now(timezone.utc)
    rows_combined = _read_jsonl(args.memory_jsonl)
    rows_a = _read_jsonl(args.memory_jsonl_a)
    rows_b = _read_jsonl(args.memory_jsonl_b)
    rows = rows_a + rows_b
    if not rows:
        rows = rows_combined

    cooled = 0
    hot_rows: list[dict[str, Any]] = []
    processed: list[dict[str, Any]] = []

    for r in rows:
        row = dict(r)
        ts = _parse_utc(str(row.get("ts_utc") or ""))
        age_days = None
        if ts is not None:
            age_days = (now - ts).total_seconds() / 86400.0
        is_expired = (age_days is not None) and (age_days > int(args.ttl_days))
        if is_expired:
            row["memory_tier"] = "cold"
            cooled += 1
        else:
            row["memory_tier"] = "warm"

        # hot promotion: reliable and conflict-free recent memory
        has_conflict = bool(((row.get("conflict_flags") or {}).get("has_conflict")))
        repro_score = int(row.get("reproducibility_score") or 0)
        if (
            (str(row.get("confidence") or "") in {"A", "B"})
            and (not has_conflict)
            and (not is_expired)
            and (repro_score >= int(args.min_repro_score))
        ):
            hot = dict(row)
            hot["memory_tier"] = "hot"
            hot_rows.append(hot)
        processed.append(row)

    # Keep latest unique (mission,state,next) triples for compact summary.
    seen = set()
    compact_lines: list[str] = []
    for row in reversed(processed):
        key = (str(row.get("mission")), str(row.get("state")), str(row.get("next")))
        if key in seen:
            continue
        seen.add(key)
        compact_lines.append(
            f"mission={row.get('mission')} | state={row.get('state')} | next={row.get('next')} | "
            f"track={row.get('track')} | conf={row.get('confidence')} | tier={row.get('memory_tier')}"
        )
        if len(compact_lines) >= int(args.compact_limit):
            break

    compact_lines = list(reversed(compact_lines))
    _write_jsonl(args.hot_jsonl, hot_rows)
    _write_jsonl(args.combined_mirror_jsonl, processed)

    args.compact_json.parent.mkdir(parents=True, exist_ok=True)
    args.compact_json.write_text(
        json.dumps(
            {
                "schema": "agent_memory_compact_20_v1",
                "generated_at_utc": _iso_now(),
                "line_count": len(compact_lines),
                "lines": compact_lines,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    args.summary_json.parent.mkdir(parents=True, exist_ok=True)
    args.summary_json.write_text(
        json.dumps(
            {
                "schema": "agent_memory_weekly_rebuild_summary_v1",
                "generated_at_utc": _iso_now(),
                "ttl_days": int(args.ttl_days),
                "total_rows": len(processed),
                "source_rows_combined": len(rows_combined),
                "source_rows_track_a": len(rows_a),
                "source_rows_track_b": len(rows_b),
                "cooled_rows": cooled,
                "hot_rows": len(hot_rows),
                "compact_line_count": len(compact_lines),
                "min_repro_score": int(args.min_repro_score),
                "status": "PASS",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "ok": True,
                "summary_json": str(args.summary_json),
                "hot_rows": len(hot_rows),
                "cooled_rows": cooled,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
