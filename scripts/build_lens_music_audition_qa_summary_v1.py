#!/usr/bin/env python3
"""Aggregate M13/M14 audition QA metrics from lens music chain reports.

M15 scope: summarize melody_stage_m13 sanity fields (peak/rms/status) across runs.
Advisory only; does not alter promotion decisions.
"""
from __future__ import annotations

import argparse
import glob
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports" / "lens_music_audition_qa_summary_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _collect_inputs(paths: list[Path], glob_pattern: str | None) -> list[Path]:
    out: list[Path] = [p for p in paths if p.is_file()]
    if glob_pattern:
        gp = str(glob_pattern)
        if Path(gp).is_absolute():
            out.extend([Path(p) for p in glob.glob(gp) if Path(p).is_file()])
        else:
            out.extend([p for p in ROOT.glob(gp) if p.is_file()])
    uniq: dict[str, Path] = {}
    for p in out:
        uniq[str(p.resolve())] = p
    return list(uniq.values())


def _mean(vals: list[float]) -> float:
    if not vals:
        return 0.0
    return float(sum(vals) / len(vals))


def build_summary(chain_paths: list[Path], *, warn_ratio_threshold: float) -> dict[str, Any]:
    parsed = 0
    with_m13 = 0
    status_counts: Counter[str] = Counter()
    note_counts: Counter[str] = Counter()
    peaks: list[float] = []
    rms_vals: list[float] = []
    seconds_vals: list[float] = []

    for path in chain_paths:
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("schema") != "lens_music_gate_chain_v1":
            continue
        parsed += 1
        m13 = doc.get("melody_stage_m13")
        if not isinstance(m13, dict):
            continue
        with_m13 += 1
        status = str(dict(m13.get("sanity_m14") or {}).get("status", "UNKNOWN"))
        status_counts[status] += 1
        for n in dict(m13.get("sanity_m14") or {}).get("notes") or []:
            note_counts[str(n)] += 1
        peaks.append(float(m13.get("peak_abs_0_1", 0.0)))
        rms_vals.append(float(m13.get("rms_0_1", 0.0)))
        seconds_vals.append(float(m13.get("seconds", 0.0)))

    warn_count = status_counts.get("WARN", 0)
    denom = max(with_m13, 1)
    warn_ratio = float(warn_count) / float(denom)
    governance_state = "WATCH" if warn_ratio > warn_ratio_threshold else "GO"

    return {
        "schema": "lens_music_audition_qa_summary_v1",
        "generated_at_utc": _utc_now(),
        "input_chain_reports": [str(p.resolve()) for p in chain_paths],
        "input_count": len(chain_paths),
        "parsed_chain_count": parsed,
        "audition_stage_count": with_m13,
        "sanity_status_counts": dict(status_counts),
        "sanity_note_counts": dict(note_counts),
        "metrics": {
            "peak_abs_mean": round(_mean(peaks), 6),
            "peak_abs_max": round(max(peaks) if peaks else 0.0, 6),
            "rms_mean": round(_mean(rms_vals), 6),
            "duration_sec_mean": round(_mean(seconds_vals), 6),
            "warn_ratio": round(warn_ratio, 6),
        },
        "governance_m16": {
            "warn_ratio_threshold": warn_ratio_threshold,
            "warn_count": int(warn_count),
            "sample_count": int(with_m13),
            "state": governance_state,
            "note": "Advisory only; does not block promotion gate decision.",
        },
        "note": "Advisory summary only; non-blocking and track_wall unchanged.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--chain-json", action="append", type=Path, default=[])
    ap.add_argument("--glob", type=str, default=None, help="Optional ROOT-relative glob for chain JSON inputs.")
    ap.add_argument(
        "--warn-ratio-threshold",
        type=float,
        default=0.2,
        help="WATCH if WARN ratio is above this threshold (default: 0.2).",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    chain_paths = _collect_inputs(args.chain_json, args.glob)
    if not chain_paths:
        print(json.dumps({"ok": False, "error": "no_input_chain_reports"}))
        return 2

    summary = build_summary(chain_paths, warn_ratio_threshold=float(args.warn_ratio_threshold))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out.resolve()), "audition_stage_count": summary["audition_stage_count"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
