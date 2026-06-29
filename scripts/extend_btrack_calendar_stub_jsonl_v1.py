#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Extend B-track calendar stub JSONL through a target date [HYPO][research_only]."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]

SASANG_SOURCE = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
SASANG_OUT = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.calendar_stub_through_202606.jsonl"
MYEONGNI_SOURCE = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
MYEONGNI_OUT = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.calendar_stub_through_202606.jsonl"

TARGETS = ("bull", "bear", "sideways")
REGIMES = ("accumulation", "distribution", "phase_transition")


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _last_date(rows: list[dict[str, Any]]) -> date | None:
    if not rows:
        return None
    ts = str(rows[-1].get("ts_utc") or "")[:10]
    if len(ts) != 10:
        return None
    return date.fromisoformat(ts)


def _sasang_row(d: date, idx: int) -> dict[str, Any]:
    target = TARGETS[idx % 3]
    regime = REGIMES[idx % 3]
    heat = round(0.45 + (idx % 10) * 0.015, 3)
    cold = round(1.0 - heat, 3)
    vol = round(0.48 + (idx % 7) * 0.02, 3)
    return {
        "ts_utc": f"{d.isoformat()}T12:00:00+00:00",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "stub": True,
        "a_track_autobind_forbidden": True,
        "mapping_target": target,
        "regime_hypothesis": regime,
        "machine_readables": {
            "heat_proxy": heat,
            "cold_proxy": cold,
            "volatility_rarefaction_proxy": vol,
        },
    }


def _myeongni_row(d: date, idx: int) -> dict[str, Any]:
    state_id = idx % 16
    target = TARGETS[idx % 3]
    consistency = round(0.58 + (idx % 8) * 0.02, 2)
    contradiction = round(0.05 + (idx % 5) * 0.012, 3)
    return {
        "ts_utc": f"{d.isoformat()}T13:00:00Z",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "stub": True,
        "state_id": state_id,
        "mapping_target": target,
        "consistency_rate": consistency,
        "self_contradiction_rate": contradiction,
        "run_id": "calendar_stub_through_202606",
    }


def extend_stub(
    *,
    source: Path,
    out_path: Path,
    through_date: str,
    row_builder: Callable[[date, int], dict[str, Any]],
) -> dict[str, Any]:
    rows = _read_jsonl(source)
    last = _last_date(rows)
    end = date.fromisoformat(through_date)
    if last is None:
        raise RuntimeError(f"No rows in source: {source}")
    if last >= end:
        out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
        return {"appended": 0, "total": len(rows), "last_date": last.isoformat(), "out_path": str(out_path)}

    start_count = len(rows)
    idx = start_count
    d = last + timedelta(days=1)
    while d <= end:
        rows.append(row_builder(d, idx))
        idx += 1
        d += timedelta(days=1)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")
    rel_out = str(out_path.relative_to(ROOT)).replace("\\", "/") if out_path.is_relative_to(ROOT) else str(out_path)
    return {
        "appended": len(rows) - start_count,
        "total": len(rows),
        "last_date": end.isoformat(),
        "out_path": rel_out,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--through-date", type=str, default="2026-06-08")
    ap.add_argument("--sasang-only", action="store_true")
    ap.add_argument("--myeongni-only", action="store_true")
    args = ap.parse_args(argv)

    results: dict[str, Any] = {"generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}
    do_both = not args.sasang_only and not args.myeongni_only
    if do_both or args.sasang_only:
        results["sasang"] = extend_stub(
            source=SASANG_SOURCE,
            out_path=SASANG_OUT,
            through_date=args.through_date,
            row_builder=_sasang_row,
        )
    if do_both or args.myeongni_only:
        results["myeongni"] = extend_stub(
            source=MYEONGNI_SOURCE,
            out_path=MYEONGNI_OUT,
            through_date=args.through_date,
            row_builder=_myeongni_row,
        )
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
