#!/usr/bin/env python3
"""명리 독립 렌즈 v0: B-track 16상 JSONL 마지막 행 → 정량 스코어 JSON (융합 대비, 비트리거)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_EXPERIMENT = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
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

# 16상 state_id 약한 prior (중립 고착 완화용, 과최적화 방지 위해 절대값 낮게 유지)
_STATE_PRIOR_SCORE: dict[int, float] = {
    6: -0.12,
    7: -0.22,
    8: -0.08,
    9: 0.18,
    10: -0.16,
    11: -0.06,
    12: 0.20,
    13: -0.10,
    14: 0.14,
    15: 0.24,
    16: -0.18,
}


def _read_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _state_id_from_row(row: dict[str, Any]) -> int | None:
    raw_sid = row.get("state_id")
    if isinstance(raw_sid, int):
        return raw_sid
    if isinstance(raw_sid, float) and raw_sid == int(raw_sid):
        return int(raw_sid)
    if isinstance(raw_sid, str) and raw_sid.strip().isdigit():
        return int(raw_sid.strip())
    return None


def _mapping_score_from_row(row: dict[str, Any]) -> float:
    mt = str(row.get("mapping_target") or "").strip().lower()
    return _MAPPING_TO_SCORE.get(mt, 0.0)


def _recent_momentum(rows: list[dict[str, Any]], window: int) -> float:
    if not rows:
        return 0.0
    tail = rows[-window:]
    vals = [_mapping_score_from_row(r) for r in tail]
    if not vals:
        return 0.0
    return sum(vals) / float(len(vals))


def _calibrate_confidence(*, consistency: float, contradiction: float, rows_seen: int) -> float:
    # 과신 방지: consistency를 contradiction으로 할인 후 표본 부족 시 0.5로 수축.
    reliability = min(1.0, max(0.2, rows_seen / 30.0))
    raw = consistency * max(0.0, 1.0 - contradiction)
    calibrated = 0.5 + (raw - 0.5) * reliability
    return max(0.05, min(0.95, calibrated))


def _build_payload(
    row: dict[str, Any],
    *,
    source: str,
    input_path: str,
    rows_seen: int,
    recent_momentum: float,
) -> dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    mt = str(row.get("mapping_target") or "").strip().lower()
    direct_score = _MAPPING_TO_SCORE.get(mt, 0.0)
    sid = _state_id_from_row(row)
    prior = _STATE_PRIOR_SCORE.get(sid or -1, 0.0)
    # 단일 행 중립값 고착 완화: 직접 신호 + 최근 모멘텀 + 약한 state prior 혼합
    direction = (0.55 * direct_score) + (0.35 * recent_momentum) + (0.10 * prior)
    if abs(direction) < 0.04:
        direction = 0.0 if abs(prior) < 0.12 else 0.08 * (1.0 if prior > 0 else -1.0)
    direction = max(-1.0, min(1.0, direction))

    cr = row.get("consistency_rate")
    sr = row.get("self_contradiction_rate")
    consistency = float(cr) if isinstance(cr, (int, float)) else 0.5
    contradiction = float(sr) if isinstance(sr, (int, float)) else 0.0
    conf = _calibrate_confidence(consistency=consistency, contradiction=contradiction, rows_seen=rows_seen)

    rationale = (
        f"B-track state_id={sid}, mapping_target={mt or 'unknown'}; "
        f"direction_score = 0.55*direct + 0.35*momentum + 0.10*state_prior, "
        f"direct={direct_score:.3f}, momentum={recent_momentum:.3f}, prior={prior:.3f}. "
        f"confidence calibrated by consistency/contradiction with sample-size shrinkage."
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
    ap.add_argument(
        "--allow-fallback",
        action="store_true",
        help="Allow embedded fallback payload when source JSONL is unavailable.",
    )
    ap.add_argument(
        "--momentum-window",
        type=int,
        default=7,
        help="Rows for recent mapping_target momentum averaging (default: 7).",
    )
    args = ap.parse_args()

    rows = _read_jsonl_rows(args.experiment_jsonl)
    row = rows[-1] if rows else None
    src = "16_state_experiment_tail"
    in_path = str(args.experiment_jsonl.resolve())
    if row is None:
        rows = _read_jsonl_rows(args.fallback_sample)
        row = rows[-1] if rows else None
        src = "sample_jsonl_fallback"
        in_path = str(args.fallback_sample.resolve())
    if row is None:
        if not args.allow_fallback:
            print(
                "myeongni lens hard-gate: no valid source row found "
                f"(missing/empty {args.experiment_jsonl} and {args.fallback_sample}). "
                "Use --allow-fallback only for manual debugging.",
            )
            return 2
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
        rows = [row]

    payload = _build_payload(
        row,
        source=src,
        input_path=in_path,
        rows_seen=len(rows),
        recent_momentum=_recent_momentum(rows, max(1, args.momentum_window)),
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
