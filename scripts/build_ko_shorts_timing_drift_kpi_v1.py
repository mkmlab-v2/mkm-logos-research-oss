#!/usr/bin/env python3
"""Aggregate P0↔P1 drift KPI across ko shorts spike artifacts [HYPO]."""

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

DEFAULT_OUT = ROOT / "reports/ko_shorts_timing_drift_kpi_v1_latest.json"
TIMING_COMPARE = ROOT / "reports/ko_shorts_timing_compare_v1_latest.json"
ALIGN_SPIKE = ROOT / "reports/ko_shorts_alignment_backend_spike_v1_latest.json"
TARGET_BATCH = ROOT / "reports/ko_shorts_target_wav_batch_v1_latest.json"

SPIKE_GLOBS = (
    "reports/ko_shorts_stt_timing_*_v1_latest.json",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _drift_row_from_spike(path: Path, doc: dict[str, Any]) -> dict[str, Any]:
    drift = dict(doc.get("drift_vs_proportional") or {})
    case_id = path.stem.replace("ko_shorts_stt_timing_", "").replace("_v1_latest", "")
    return {
        "case_id": case_id,
        "spike_json": _rel(path),
        "aligned_word_count": doc.get("aligned_word_count"),
        "p1_segment_count": doc.get("p1_segment_count"),
        "start_drift_ms_mean": drift.get("start_drift_ms_mean"),
        "end_drift_ms_mean": drift.get("end_drift_ms_mean"),
        "start_drift_ms_max": drift.get("start_drift_ms_max"),
        "end_drift_ms_max": drift.get("end_drift_ms_max"),
        "pairs": drift.get("pairs"),
    }


def collect_spike_drift_rows_v1() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for pattern in SPIKE_GLOBS:
        for path in sorted(ROOT.glob(pattern)):
            doc = _read_json(path)
            if not doc:
                continue
            rows.append(_drift_row_from_spike(path, doc))
    return sorted(rows, key=lambda r: str(r.get("case_id") or ""))


def build_drift_kpi_v1() -> dict[str, Any]:
    compare = _read_json(TIMING_COMPARE)
    align = _read_json(ALIGN_SPIKE)
    batch = _read_json(TARGET_BATCH)
    spike_rows = collect_spike_drift_rows_v1()

    alignment_by_case: dict[str, dict[str, Any]] = {}
    for case in (align or {}).get("cases") or []:
        cid = str(case.get("case_id") or "")
        if cid:
            alignment_by_case[cid] = {
                "applied_backend": case.get("applied_backend"),
                "start_drift_ms_mean": case.get("start_drift_ms_mean"),
                "routing_rule_id": case.get("routing_rule_id"),
            }

    merged: list[dict[str, Any]] = []
    for row in spike_rows:
        cid = str(row.get("case_id") or "")
        entry = dict(row)
        if cid in alignment_by_case:
            entry["alignment_routed"] = alignment_by_case[cid]
        merged.append(entry)

    start_vals = [r["start_drift_ms_mean"] for r in merged if r.get("start_drift_ms_mean") is not None]
    gate_runs = list((batch or {}).get("runs") or [])

    return {
        "schema": "ko_shorts_timing_drift_kpi_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "drift_note": "start/end_drift_ms_mean = P0 proportional vs P1 aligned gap; not lip-sync pass",
        "sources": {
            "timing_compare": str(TIMING_COMPARE.relative_to(ROOT)).replace("\\", "/") if compare else None,
            "alignment_spike": str(ALIGN_SPIKE.relative_to(ROOT)).replace("\\", "/") if align else None,
            "target_batch": str(TARGET_BATCH.relative_to(ROOT)).replace("\\", "/") if batch else None,
        },
        "clinical_sim_spectrum": (compare or {}).get("clinical_sim_spectrum"),
        "spike_drift_rows": merged,
        "summary": {
            "case_count": len(merged),
            "start_drift_ms_mean_min": min(start_vals) if start_vals else None,
            "start_drift_ms_mean_max": max(start_vals) if start_vals else None,
            "target_batch_ok_count": (batch or {}).get("ok_count"),
            "target_batch_total": (batch or {}).get("total"),
        },
        "target_batch_runs": gate_runs,
        "reproduce": "py scripts/build_ko_shorts_timing_drift_kpi_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    report = build_drift_kpi_v1()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "case_count": report["summary"]["case_count"],
                "start_drift_range": [
                    report["summary"]["start_drift_ms_mean_min"],
                    report["summary"]["start_drift_ms_mean_max"],
                ],
                "out": str(out).replace("\\", "/"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
