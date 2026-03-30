#!/usr/bin/env python3
"""Collect B-Track pilot quality metrics from paired A/B JSONL outputs.

Expected input: line-delimited JSON objects from A-track and B-track evaluation runs.
The script aligns rows by query key and emits:
  - reproducibility: direction match rate
  - resolution: confidence delta (B - A)
  - contamination: SNR delta (B - A, if available)
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_A = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "a_track_eval.jsonl"
DEFAULT_B = ROOT / "data" / "logos" / "btrack_pilot" / "bench" / "b_track_eval.jsonl"
DEFAULT_REPORT = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_quality_latest.json"
DEFAULT_DETAILS = ROOT / "reports" / "constitution" / "btrack_pilot" / "btrack_pair_details_latest.jsonl"


@dataclass
class EvalRow:
    key: str
    direction: str | None
    confidence: float | None
    snr: float | None
    raw: dict[str, Any]


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _first_str(row: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for k in keys:
        v = row.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def _first_float(row: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    for k in keys:
        v = row.get(k)
        if isinstance(v, (int, float)):
            return float(v)
        if isinstance(v, str):
            try:
                return float(v)
            except ValueError:
                continue
    return None


def _infer_direction(row: dict[str, Any]) -> str | None:
    direct = _first_str(row, ("direction", "prediction", "mapping_target", "label"))
    if direct:
        return direct.lower()
    signed = _first_float(row, ("score", "logit", "signed_score", "delta"))
    if signed is None:
        return None
    if signed > 0:
        return "up"
    if signed < 0:
        return "down"
    return "flat"


def _row_key(row: dict[str, Any], fallback_index: int) -> str:
    primary = _first_str(
        row,
        (
            "query_id",
            "sample_id",
            "id",
            "lookup_id_ref",
            "verse_id",
            "state_id",
            "canonical_ref",
        ),
    )
    if primary:
        return primary
    return f"row_{fallback_index:08d}"


def load_rows(path: Path) -> dict[str, EvalRow]:
    out: dict[str, EvalRow] = {}
    with path.open("r", encoding="utf-8") as f:
        for idx, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if not isinstance(row, dict):
                continue
            key = _row_key(row, idx)
            out[key] = EvalRow(
                key=key,
                direction=_infer_direction(row),
                confidence=_first_float(row, ("confidence", "probability", "score_abs", "consistency_rate")),
                snr=_first_float(row, ("snr", "signal_to_noise", "signal_noise_ratio")),
                raw=row,
            )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Collect B-Track quality metrics from paired A/B JSONL")
    ap.add_argument("--a", dest="a_path", default=str(DEFAULT_A), help="A-track JSONL path")
    ap.add_argument("--b", dest="b_path", default=str(DEFAULT_B), help="B-track JSONL path")
    ap.add_argument("--out", dest="out_path", default=str(DEFAULT_REPORT), help="Output JSON report path")
    ap.add_argument("--details-out", dest="details_out", default=str(DEFAULT_DETAILS), help="Output per-pair JSONL path")
    args = ap.parse_args()

    a_path = _abs(args.a_path)
    b_path = _abs(args.b_path)
    out_path = _abs(args.out_path)
    details_path = _abs(args.details_out)

    if not a_path.is_file():
        print(f"ERROR: missing A-track file: {a_path}")
        return 2
    if not b_path.is_file():
        print(f"ERROR: missing B-track file: {b_path}")
        return 2

    a_rows = load_rows(a_path)
    b_rows = load_rows(b_path)
    keys = sorted(set(a_rows) & set(b_rows))

    if not keys:
        print("ERROR: no aligned keys between A and B inputs")
        return 3

    direction_compared = 0
    direction_match = 0
    confidence_deltas: list[float] = []
    snr_deltas: list[float] = []
    details: list[dict[str, Any]] = []

    for key in keys:
        a = a_rows[key]
        b = b_rows[key]

        matched: bool | None = None
        if a.direction and b.direction:
            direction_compared += 1
            matched = a.direction == b.direction
            if matched:
                direction_match += 1

        conf_delta: float | None = None
        if a.confidence is not None and b.confidence is not None:
            conf_delta = b.confidence - a.confidence
            confidence_deltas.append(conf_delta)

        snr_delta: float | None = None
        if a.snr is not None and b.snr is not None:
            snr_delta = b.snr - a.snr
            snr_deltas.append(snr_delta)

        details.append(
            {
                "key": key,
                "a_direction": a.direction,
                "b_direction": b.direction,
                "direction_match": matched,
                "a_confidence": a.confidence,
                "b_confidence": b.confidence,
                "confidence_delta_b_minus_a": conf_delta,
                "a_snr": a.snr,
                "b_snr": b.snr,
                "snr_delta_b_minus_a": snr_delta,
            }
        )

    reproducibility = (direction_match / direction_compared) if direction_compared else None
    resolution_delta = mean(confidence_deltas) if confidence_deltas else None
    contamination_delta = mean(snr_deltas) if snr_deltas else None

    report = {
        "schema": "btrack_quality_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "a_track": str(a_path),
            "b_track": str(b_path),
        },
        "counts": {
            "a_rows": len(a_rows),
            "b_rows": len(b_rows),
            "aligned_pairs": len(keys),
            "direction_compared": direction_compared,
            "confidence_compared": len(confidence_deltas),
            "snr_compared": len(snr_deltas),
        },
        "metrics": {
            "reproducibility_match_rate": reproducibility,
            "resolution_confidence_delta_b_minus_a": resolution_delta,
            "contamination_snr_delta_b_minus_a": contamination_delta,
        },
        "interpretation": {
            "reproducibility": "higher is better",
            "resolution": ">= 0 means B-track confidence does not degrade on average",
            "contamination": ">= 0 means B-track SNR does not degrade on average",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    details_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with details_path.open("w", encoding="utf-8") as f:
        for row in details:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print("OK: btrack quality report generated")
    print(f"report: {out_path}")
    print(f"details: {details_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
