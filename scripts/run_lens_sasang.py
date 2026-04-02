#!/usr/bin/env python3
"""사상(Sasang) 독립 렌즈 v0: B-track dynamics JSONL 마지막 행 → 정량 스코어 (비의료·비트리거)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "data" / "sasang" / "sasang_dynamics_regime_mapping_v1.sample.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "sasang_independent_lens_latest.json"

ARTIFACT_SCHEMA = "sasang_independent_lens_v0"
ENGINE_ID = "independent_lens_v0"
VERSION = "0.1.0"

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


def _confidence_from_machine(row: dict[str, Any]) -> float:
    mr = row.get("machine_readables")
    if not isinstance(mr, dict):
        return 0.5
    vals: list[float] = []
    for k in ("heat_proxy", "cold_proxy", "volatility_rarefaction_proxy"):
        v = mr.get(k)
        if isinstance(v, (int, float)):
            vals.append(float(v))
    if not vals:
        return 0.5
    return max(0.0, min(1.0, sum(vals) / len(vals)))


def _build_payload(row: dict[str, Any], *, source: str, input_path: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mt = str(row.get("mapping_target") or "").strip().lower()
    direction = _MAPPING_TO_SCORE.get(mt, 0.0)
    conf = _confidence_from_machine(row)

    rationale = (
        f"B-track sasang regime_hypothesis={row.get('regime_hypothesis')!s}, "
        f"mapping_target={mt or 'unknown'}; machine_readables averaged for confidence (v0)."
    )
    return {
        "schema": ARTIFACT_SCHEMA,
        "version": VERSION,
        "lens_id": "sasang",
        "engine_id": ENGINE_ID,
        "ts_utc": now,
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "a_track_autobind_forbidden": True,
        "scores": {
            "direction_score": round(direction, 6),
            "confidence": round(conf, 6),
        },
        "sasang_stream_outputs": {
            "regime_hypothesis": row.get("regime_hypothesis"),
            "machine_readables": row.get("machine_readables"),
            "mapping_target": mt or None,
            "rationale": rationale,
        },
        "provenance": {
            "source": source,
            "input_path": input_path,
            "row_ts_utc": str(row.get("ts_utc") or ""),
        },
        "note": "B-track observation only; not medical advice; not live trading trigger; fusion-ready numeric stub.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Emit sasang independent lens v0 JSON from dynamics JSONL tail.")
    ap.add_argument("--input-jsonl", type=Path, default=DEFAULT_JSONL)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    row = _tail_jsonl_row(args.input_jsonl)
    src = "sasang_dynamics_jsonl_tail"
    in_path = str(args.input_jsonl.resolve())
    if row is None:
        row = {
            "ts_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00"),
            "hypothesis_tier": "B",
            "boundary_ack": True,
            "a_track_autobind_forbidden": True,
            "machine_readables": {"heat_proxy": 0.33, "cold_proxy": 0.33, "volatility_rarefaction_proxy": 0.34},
            "regime_hypothesis": "unspecified",
            "mapping_target": "sideways",
            "note": "embedded_minimal_fallback",
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
