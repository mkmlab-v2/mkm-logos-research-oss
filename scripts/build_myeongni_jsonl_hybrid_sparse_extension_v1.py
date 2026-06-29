#!/usr/bin/env python3
"""Merge sparse 202604 JSONL + manseryeok session rows for dates after base tail (B-track).

Purpose: extend sidecar coverage into KOSPI OOS window without replacing pre-202605 stub rows.
research_only — compare OOS hit vs golden sparse_orig before any promote.
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
DEFAULT_MYEONGNI_OUT = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.hybrid_sparse_session_ext_v1.jsonl"
DEFAULT_SASANG_OUT = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.hybrid_sparse_session_ext_v1.jsonl"


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


def _merge(
    base: dict[str, dict[str, Any]],
    extension: dict[str, dict[str, Any]],
    *,
    extend_after: str | None,
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    cut = date.fromisoformat(extend_after) if extend_after else None
    merged: dict[str, dict[str, Any]] = dict(base)
    stats = {"base_days": len(base), "extension_applied": 0, "extension_skipped_overlap": 0}
    for ed, row in sorted(extension.items()):
        try:
            d = date.fromisoformat(ed)
        except ValueError:
            continue
        if cut is not None and d <= cut:
            if ed in merged:
                stats["extension_skipped_overlap"] += 1
            continue
        ext_row = dict(row)
        ext_row["source"] = "hybrid_extension_manseryeok_session_v1"
        ext_row["hypothesis_tier"] = "B"
        ext_row["boundary_ack"] = True
        ext_row["stub"] = False
        merged[ed] = ext_row
        stats["extension_applied"] += 1
    lines = [merged[k] for k in sorted(merged)]
    return lines, stats


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--base-myeongni", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--session-myeongni", type=Path, default=DEFAULT_SESSION)
    ap.add_argument("--base-sasang", type=Path, default=DEFAULT_SASANG_BASE)
    ap.add_argument("--session-sasang", type=Path, default=DEFAULT_SASANG_SESSION)
    ap.add_argument(
        "--extend-after",
        default=None,
        help="Apply session extension only for dates strictly after YYYY-MM-DD (default: max day in base JSONL).",
    )
    ap.add_argument("--myeongni-out", type=Path, default=DEFAULT_MYEONGNI_OUT)
    ap.add_argument("--sasang-out", type=Path, default=DEFAULT_SASANG_OUT)
    args = ap.parse_args()

    base_m = _load_jsonl_by_day(args.base_myeongni)
    sess_m = _load_jsonl_by_day(args.session_myeongni)
    extend_after = args.extend_after
    if not extend_after and base_m:
        extend_after = max(base_m)
    my_lines, st_m = _merge(base_m, sess_m, extend_after=extend_after)

    base_s = _load_jsonl_by_day(args.base_sasang)
    sess_s = _load_jsonl_by_day(args.session_sasang)
    sa_lines, st_s = _merge(base_s, sess_s, extend_after=extend_after)

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
        "schema": "myeongni_jsonl_hybrid_sparse_extension_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "extend_after": extend_after,
        "myeongni_stats": st_m,
        "sasang_stats": st_s,
        "n_lines": len(my_lines),
        "myeongni_out": str(args.myeongni_out.relative_to(ROOT)).replace("\\", "/"),
        "sasang_out": str(args.sasang_out.relative_to(ROOT)).replace("\\", "/"),
    }
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
