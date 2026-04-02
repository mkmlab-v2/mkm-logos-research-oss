#!/usr/bin/env python3
"""명리 독립 렌즈 v0: B-track 16상 JSONL 마지막 행 → 정량 스코어 JSON (융합 대비, 비트리거)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_v1.jsonl"
DEFAULT_SAMPLE = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_v1.sample.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"

ARTIFACT_SCHEMA = "myeongni_independent_lens_v0"
ENGINE_ID = "independent_lens_v0"
VERSION = "0.1.0"

# mapping_target (B-track 실험) → direction_score; 가설 티어 B 전용 휴리스틱
_MAPPING_TO_SCORE: dict[str, float] = {
    "bull": 0.55,
    "bear": -0.55,
    "sideways": 0.0,
}


def _tail_jsonl_row(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    last: dict[str, Any] | None = None
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            last = obj
    return last


def _build_payload(row: dict[str, Any], *, source: str, input_path: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mt = str(row.get("mapping_target") or "").strip().lower()
    direction = _MAPPING_TO_SCORE.get(mt, 0.0)
    cr = row.get("consistency_rate")
    conf = float(cr) if isinstance(cr, (int, float)) else 0.5
    conf = max(0.0, min(1.0, conf))

    raw_sid = row.get("state_id")
    sid: int | None = None
    if isinstance(raw_sid, int):
        sid = raw_sid
    elif isinstance(raw_sid, float) and raw_sid == int(raw_sid):
        sid = int(raw_sid)
    elif isinstance(raw_sid, str) and raw_sid.strip().isdigit():
        sid = int(raw_sid.strip())

    rationale = (
        f"B-track state_id={sid}, mapping_target={mt or 'unknown'}; "
        f"direction_score from curated mapping_target heuristic (v0)."
    )
    row_ts = str(row.get("ts_utc") or "")

    return {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "lens_id": "myeongni",
        "engine_id": ENGINE_ID,
        "ts_utc": now,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "scores": {
            "direction_score": round(direction, 6),
            "confidence": round(conf, 6),
        },
        "myeongri_stream_outputs": {
            "myeongri_gapja": row.get("myeongri_gapja"),
            "state_id": sid,
            "experiment_id": row.get("experiment_id"),
            "run_id": row.get("run_id"),
            "rationale": rationale,
        },
        "provenance": {
            "source": source,
            "input_path": input_path,
            "row_ts_utc": row_ts,
        },
        "note": "B-track independent lens v0; not A-track / not dual_regime cap; fusion-ready numeric stub only.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit myeongni independent lens v0 JSON from B-track experiment JSONL tail.")
    ap.add_argument("--experiment-jsonl", type=Path, default=DEFAULT_EXPERIMENT)
    ap.add_argument("--fallback-sample", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    row = _tail_jsonl_row(args.experiment_jsonl)
    src = "16_state_experiment_tail"
    in_path = str(args.experiment_jsonl.resolve())
    if row is None:
        row = _tail_jsonl_row(args.fallback_sample)
        src = "sample_jsonl_fallback"
        in_path = str(args.fallback_sample.resolve())
    if row is None:
        row = {
            "experiment_id": "exp_16state_v1",
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "stub": True,
            "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "state_id": None,
            "mapping_target": "sideways",
            "consistency_rate": 0.5,
            "run_id": "lens_v0_empty_fallback",
            "note": "No experiment JSONL; minimal stub row",
        }
        src = "embedded_minimal_fallback"
        in_path = ""

    payload = _build_payload(row, source=src, input_path=in_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
