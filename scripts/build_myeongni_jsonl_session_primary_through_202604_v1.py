#!/usr/bin/env python3
"""[HYPO] Session rows replace sparse calendar stub for dates through 202604 (B-track A/B)."""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STUB = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
DEFAULT_SESSION = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_SASANG_STUB = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
DEFAULT_SASANG_SESSION = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"
DEFAULT_MYEONGNI_OUT = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.session_primary_through_202604_v1.jsonl"
DEFAULT_SASANG_OUT = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.session_primary_through_202604_v1.jsonl"
DEFAULT_CUTOFF = "2026-04-30"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl_by_day(path: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        ed = str(row.get("eval_date") or row.get("ts_utc") or "")[:10]
        if ed:
            out[ed] = row
    return out


def _merge_session_primary(
    stub: dict[str, dict[str, Any]],
    session: dict[str, dict[str, Any]],
    *,
    cutoff: str,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    cut = date.fromisoformat(cutoff)
    merged: dict[str, dict[str, Any]] = {}
    stats = {
        "stub_days": len(stub),
        "session_days": len(session),
        "session_applied_le_cutoff": 0,
        "session_applied_gt_cutoff": 0,
        "stub_only_gt_cutoff": 0,
    }
    for ed, row in session.items():
        try:
            d = date.fromisoformat(ed)
        except ValueError:
            continue
        r = dict(row)
        r["source"] = "session_primary_through_202604_v1"
        r["hypothesis_tier"] = "B"
        r["boundary_ack"] = True
        r["stub"] = False
        merged[ed] = r
        if d <= cut:
            stats["session_applied_le_cutoff"] += 1
        else:
            stats["session_applied_gt_cutoff"] += 1
    for ed, row in stub.items():
        try:
            d = date.fromisoformat(ed)
        except ValueError:
            continue
        if d > cut and ed not in merged:
            merged[ed] = dict(row)
            stats["stub_only_gt_cutoff"] += 1
    lines = [merged[k] for k in sorted(merged)]
    return lines, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--stub-myeongni", type=Path, default=DEFAULT_STUB)
    ap.add_argument("--session-myeongni", type=Path, default=DEFAULT_SESSION)
    ap.add_argument("--stub-sasang", type=Path, default=DEFAULT_SASANG_STUB)
    ap.add_argument("--session-sasang", type=Path, default=DEFAULT_SASANG_SESSION)
    ap.add_argument("--cutoff", default=DEFAULT_CUTOFF)
    ap.add_argument("--myeongni-out", type=Path, default=DEFAULT_MYEONGNI_OUT)
    ap.add_argument("--sasang-out", type=Path, default=DEFAULT_SASANG_OUT)
    args = ap.parse_args()

    stub_m = _load_jsonl_by_day(args.stub_myeongni)
    sess_m = _load_jsonl_by_day(args.session_myeongni)
    my_lines, st_m = _merge_session_primary(stub_m, sess_m, cutoff=args.cutoff)

    stub_s = _load_jsonl_by_day(args.stub_sasang)
    sess_s = _load_jsonl_by_day(args.session_sasang)
    sa_lines, st_s = _merge_session_primary(stub_s, sess_s, cutoff=args.cutoff)

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
        "schema": "myeongni_jsonl_session_primary_through_202604_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "cutoff": args.cutoff,
        "myeongni_stats": st_m,
        "sasang_stats": st_s,
        "n_lines": len(my_lines),
        "myeongni_out": str(args.myeongni_out.relative_to(ROOT)).replace("\\", "/"),
        "sasang_out": str(args.sasang_out.relative_to(ROOT)).replace("\\", "/"),
        "note_ko": "≤cutoff 구간 sparse stub 대신 session 전량; >cutoff는 session 우선·stub 보조.",
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
