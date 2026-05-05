#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Emit one JSONL row for eval_multilens_harness_v2_thin.py --populate-default-samples.

Bridges `myeongni_independent_lens_latest.json` (scores, provenance) with the **same**
16-state experiment tail row shape expected by overlap JSONL (`mapping_target`, `vector_4d`),
keyed by `--calendar-date` so Thin rows pick up `myeongni_b_track` for that date.

Does not replace `myeongni_curated_overlap_v1.jsonl`; use `--out` to a dedicated bridge file and pass
`--myeongni-jsonl` to the thin harness when comparing lens-vs-stub provenance.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_LENS = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"


def _parse_iso_to_utc_date(s: str) -> date:
    s = str(s).strip()
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc)
    return dt.date()


def _anchor_date_from_lens(lens: dict[str, Any]) -> date:
    ts = lens.get("ts_utc")
    if ts:
        try:
            return _parse_iso_to_utc_date(str(ts))
        except ValueError:
            pass
    prov = lens.get("provenance")
    if isinstance(prov, dict) and prov.get("row_ts_utc"):
        try:
            return _parse_iso_to_utc_date(str(prov["row_ts_utc"]))
        except ValueError:
            pass
    return datetime.now(timezone.utc).date()


def resolve_calendar_date_auto(
    lens: dict[str, Any],
    *,
    curated_path: Path,
) -> str:
    """Pick `dates[]` entry minimizing calendar distance from lens anchor date."""
    raw = _read_json(curated_path)
    if not raw:
        raise ValueError(f"missing or invalid curated dates JSON: {curated_path}")
    dates = raw.get("dates")
    if not isinstance(dates, list) or not dates:
        raise ValueError("curated dates: 'dates' must be a non-empty list")
    anchor = _anchor_date_from_lens(lens)
    best: str | None = None
    best_delta: int | None = None
    for ds in dates:
        if not isinstance(ds, str) or len(ds) < 10:
            continue
        d0 = ds[:10]
        try:
            cd = date.fromisoformat(d0)
        except ValueError:
            continue
        delta = abs((anchor - cd).days)
        if best_delta is None or delta < best_delta:
            best_delta = delta
            best = d0
    if not best:
        raise ValueError("no valid YYYY-MM-DD entries in curated dates")
    return best


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _last_jsonl_row(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    last: dict[str, Any] | None = None
    for raw in path.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            last = obj
    return last


def _mapping_target_from_rationale(lens: dict[str, Any]) -> str:
    mso = lens.get("myeongri_stream_outputs")
    if not isinstance(mso, dict):
        return ""
    rat = str(mso.get("rationale") or "")
    match = re.search(r"mapping_target=(\w+)", rat)
    return match.group(1).strip().lower() if match else ""


def build_bridge_line(
    *,
    lens: dict[str, Any],
    experiment_tail: dict[str, Any] | None,
    calendar_date: str,
) -> dict[str, Any]:
    """calendar_date: YYYY-MM-DD — sets ts_utc noon UTC for overlap indexing."""
    if len(calendar_date) < 10:
        raise ValueError("calendar_date must be YYYY-MM-DD")
    ts_utc = f"{calendar_date[:10]}T12:00:00.000Z"
    exp = experiment_tail or {}
    mt = str(exp.get("mapping_target") or "").strip().lower()
    if not mt:
        mt = _mapping_target_from_rationale(lens)
    if not mt:
        mt = "sideways"
    sid = exp.get("state_id")
    if sid is None:
        mso = lens.get("myeongri_stream_outputs")
        if isinstance(mso, dict) and mso.get("state_id") is not None:
            sid = mso.get("state_id")
    v4 = exp.get("vector_4d")
    if not isinstance(v4, dict):
        v4 = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    scores = lens.get("scores") if isinstance(lens.get("scores"), dict) else {}
    line: dict[str, Any] = {
        "experiment_id": exp.get("experiment_id") or "bridge_from_independent_lens_v1",
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "stub": False,
        "bridge_version": "myeongni_thin_bridge_v1",
        "ts_utc": ts_utc,
        "state_id": sid,
        "mapping_target": mt,
        "vector_4d": {k: float(v4[k]) for k in ("S", "L", "K", "M") if k in v4},
        "note": "emit_myeongni_thin_bridge_line_v1: joins independent_lens_latest + experiment tail",
        "independent_lens_snapshot": {
            "direction_score": scores.get("direction_score"),
            "confidence": scores.get("confidence"),
            "lens_ts_utc": lens.get("ts_utc"),
            "provenance_input_path": (lens.get("provenance") or {}).get("input_path"),
        },
    }
    if len(line["vector_4d"]) != 4:
        line["vector_4d"] = {"S": 0.25, "L": 0.25, "K": 0.25, "M": 0.25}
    return line


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument(
        "--experiment-jsonl",
        type=Path,
        default=None,
        help="Override experiment JSONL (default: provenance.input_path from lens JSON)",
    )
    ap.add_argument(
        "--curated-dates-json",
        type=Path,
        default=None,
        help="For --calendar-date auto: grid file (default: data/multilens_eval/curated_dates_v1.json)",
    )
    ap.add_argument(
        "--calendar-date",
        default="auto",
        help="YYYY-MM-DD on the Thin bench grid, or 'auto' (nearest grid day to lens ts_utc / row_ts_utc)",
    )
    ap.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write single-line JSONL (overwrite). Default: stdout",
    )
    args = ap.parse_args()
    root = args.workspace_root.resolve()
    lens_path = args.lens_json if args.lens_json.is_absolute() else (root / args.lens_json)
    lens = _read_json(lens_path)
    if not lens:
        print(f"FAIL: missing or invalid lens JSON: {lens_path}", file=sys.stderr)
        return 2

    exp_path = args.experiment_jsonl
    if exp_path is None:
        prov = lens.get("provenance")
        ip = str((prov or {}).get("input_path") or "").strip()
        exp_path = Path(ip) if ip else None
    else:
        exp_path = args.experiment_jsonl if args.experiment_jsonl.is_absolute() else (root / args.experiment_jsonl)

    exp_tail = _last_jsonl_row(exp_path) if exp_path and exp_path.is_file() else None
    if exp_tail is None and exp_path:
        print(f"WARN: experiment JSONL missing or empty: {exp_path}", file=sys.stderr)

    cal_in = (args.calendar_date or "auto").strip()
    curated_for_auto = args.curated_dates_json
    if curated_for_auto is None:
        curated_for_auto = root / "data" / "multilens_eval" / "curated_dates_v1.json"
    elif not curated_for_auto.is_absolute():
        curated_for_auto = root / curated_for_auto

    if cal_in.lower() == "auto":
        try:
            resolved = resolve_calendar_date_auto(lens, curated_path=curated_for_auto)
        except ValueError as e:
            print(f"FAIL: {e}", file=sys.stderr)
            return 2
        print(
            f"emit_myeongni_thin_bridge: calendar_date(auto)={resolved} "
            f"(curated={curated_for_auto.name})",
            file=sys.stderr,
        )
        cal_use = resolved
    else:
        cal_use = cal_in

    try:
        line = build_bridge_line(
            lens=lens,
            experiment_tail=exp_tail,
            calendar_date=cal_use,
        )
    except ValueError as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 2

    payload = json.dumps(line, ensure_ascii=False)
    if args.out:
        out = args.out if args.out.is_absolute() else (root / args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(payload + "\n", encoding="utf-8")
        print(f"WROTE: {out}")
    else:
        print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
