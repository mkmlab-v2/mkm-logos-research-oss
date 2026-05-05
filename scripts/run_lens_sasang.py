#!/usr/bin/env python3
"""사상(Sasang) 독립 렌즈 v0: B-track dynamics JSONL 마지막 행 → 정량 스코어 (비의료·비트리거)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSONL = ROOT / "data" / "sasang" / "sasang_dynamics_regime_mapping_v1.calendar_stub_through_202604.jsonl"
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
    heat = float(mr.get("heat_proxy")) if isinstance(mr.get("heat_proxy"), (int, float)) else None
    cold = float(mr.get("cold_proxy")) if isinstance(mr.get("cold_proxy"), (int, float)) else None
    vol = float(mr.get("volatility_rarefaction_proxy")) if isinstance(mr.get("volatility_rarefaction_proxy"), (int, float)) else None
    if heat is None or cold is None or vol is None:
        return 0.5
    # Confidence baseline + proxy separation bonus. This avoids chronic sub-0.55 scores
    # when directional proxies are mildly imbalanced yet consistent.
    imbalance = abs(heat - cold)
    conf = 0.45 + (0.35 * vol) + (0.55 * imbalance)
    return max(0.0, min(1.0, conf))


def _direction_from_mapping(row: dict[str, Any], mapping_target: str) -> float:
    base = _MAPPING_TO_SCORE.get(mapping_target, 0.0)
    if mapping_target != "sideways":
        return base
    mr = row.get("machine_readables")
    if not isinstance(mr, dict):
        return 0.0
    heat = float(mr.get("heat_proxy")) if isinstance(mr.get("heat_proxy"), (int, float)) else None
    cold = float(mr.get("cold_proxy")) if isinstance(mr.get("cold_proxy"), (int, float)) else None
    if heat is None or cold is None:
        return 0.0
    delta = heat - cold
    # Neutral anchor with micro-tilt: keep small bounded signal and prevent hard 0 fixation.
    if abs(delta) < 0.02:
        return 0.0
    return max(-0.18, min(0.18, delta))


def _build_payload(row: dict[str, Any], *, source: str, input_path: str) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mt = str(row.get("mapping_target") or "").strip().lower()
    direction = _direction_from_mapping(row, mt)
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
    ap.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Allow fallback payload or missing mapping_target for manual debugging only.",
    )
    args = ap.parse_args()

    row = _tail_jsonl_row(args.input_jsonl)
    src = "sasang_dynamics_jsonl_tail"
    in_path = str(args.input_jsonl.resolve())
    mt = str((row or {}).get("mapping_target") or "").strip().lower() if isinstance(row, dict) else ""
    valid_mapping = mt in _MAPPING_TO_SCORE
    if row is not None and (not valid_mapping) and (not args.allow_fallback):
        print(
            "sasang lens hard-gate: mapping_target missing/invalid in source row "
            f"({args.input_jsonl}). Use --allow-fallback only for manual debugging."
        )
        return 2
    if row is None:
        if not args.allow_fallback:
            print(
                "sasang lens hard-gate: no valid source row found "
                f"(missing/empty {args.input_jsonl}). Use --allow-fallback only for manual debugging."
            )
            return 2
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
