#!/usr/bin/env python3
"""[HYPO] Sparse 202604 stub + session overlay on blind OOS window + post-cutoff extension.

Keeps calendar stub outside blind; fills 2025-05-21..2025-11-24 from manseryeok session
so golden/hybrid can be re-tested on blind vs confirm stability.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BASE = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
DEFAULT_SESSION = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_BASE = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
DEFAULT_SASANG_SESSION = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_MYEONGNI_OUT = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.sparse_blind_session_fill_v1.jsonl"
DEFAULT_SASANG_OUT = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.sparse_blind_session_fill_v1.jsonl"
DEFAULT_BLIND_START = "2025-05-21"
DEFAULT_BLIND_END = "2025-11-24"
DEFAULT_EXTEND_AFTER = "2026-04-30"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _day_from_row(row: dict[str, Any]) -> str:
    return str(row.get("eval_date") or row.get("ts_utc") or "")[:10]


def _load_jsonl_by_day(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        ed = _day_from_row(row)
        if ed:
            out[ed] = row
    return out


def _merge_blind_fill(
    base: dict[str, dict[str, Any]],
    session: dict[str, dict[str, Any]],
    *,
    blind_start: str,
    blind_end: str,
    extend_after: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    b0 = date.fromisoformat(blind_start)
    b1 = date.fromisoformat(blind_end)
    cut = date.fromisoformat(extend_after)
    merged: dict[str, dict[str, Any]] = dict(base)
    stats = {
        "base_days": len(base),
        "blind_session_fill": 0,
        "post_cutoff_session_ext": 0,
        "session_skipped_outside_blind_and_cutoff": 0,
    }
    for ed, row in sorted(session.items()):
        try:
            d = date.fromisoformat(ed)
        except ValueError:
            continue
        r = dict(row)
        r["hypothesis_tier"] = "B"
        r["boundary_ack"] = True
        if b0 <= d <= b1:
            r["source"] = "blind_window_session_fill_v1"
            r["stub"] = False
            merged[ed] = r
            stats["blind_session_fill"] += 1
        elif d > cut:
            r["source"] = "blind_window_session_fill_post_cutoff_v1"
            r["stub"] = False
            merged[ed] = r
            stats["post_cutoff_session_ext"] += 1
        else:
            stats["session_skipped_outside_blind_and_cutoff"] += 1
    lines = [merged[k] for k in sorted(merged)]
    return lines, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-myeongni", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--session-myeongni", type=Path, default=DEFAULT_SESSION)
    ap.add_argument("--base-sasang", type=Path, default=DEFAULT_SASANG_BASE)
    ap.add_argument("--session-sasang", type=Path, default=DEFAULT_SASANG_SESSION)
    ap.add_argument("--blind-start", default=DEFAULT_BLIND_START)
    ap.add_argument("--blind-end", default=DEFAULT_BLIND_END)
    ap.add_argument("--extend-after", default=DEFAULT_EXTEND_AFTER)
    ap.add_argument("--myeongni-out", type=Path, default=DEFAULT_MYEONGNI_OUT)
    ap.add_argument("--sasang-out", type=Path, default=DEFAULT_SASANG_OUT)
    args = ap.parse_args()

    base_m = _load_jsonl_by_day(args.base_myeongni)
    sess_m = _load_jsonl_by_day(args.session_myeongni)
    my_lines, st_m = _merge_blind_fill(
        base_m,
        sess_m,
        blind_start=args.blind_start,
        blind_end=args.blind_end,
        extend_after=args.extend_after,
    )

    base_s = _load_jsonl_by_day(args.base_sasang)
    sess_s = _load_jsonl_by_day(args.session_sasang)
    sa_lines, st_s = _merge_blind_fill(
        base_s,
        sess_s,
        blind_start=args.blind_start,
        blind_end=args.blind_end,
        extend_after=args.extend_after,
    )

    args.myeongni_out.parent.mkdir(parents=True, exist_ok=True)
    args.sasang_out.parent.mkdir(parents=True, exist_ok=True)
    args.myeongni_out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in my_lines) + "\n",
        encoding="utf-8",
    )
    args.sasang_out.write_text(
        "\n".join(json.dumps(x, ensure_ascii=False) for x in sa_lines) + "\n",
        encoding="utf-8",
    )

    meta = {
        "schema": "myeongni_jsonl_blind_window_session_fill_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "blind_window": {"start": args.blind_start, "end": args.blind_end},
        "extend_after": args.extend_after,
        "myeongni_stats": st_m,
        "sasang_stats": st_s,
        "n_lines": len(my_lines),
        "myeongni_out": str(args.myeongni_out.relative_to(ROOT)).replace("\\", "/"),
        "note_ko": "golden sparse stub 유지 + blind 구간·202605+ 만 session 오버레이.",
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
