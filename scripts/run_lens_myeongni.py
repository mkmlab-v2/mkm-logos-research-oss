#!/usr/bin/env python3
"""명리 독립 렌즈 v0/v1: B-track 16상 JSONL 마지막 행 → 정량 스코어 JSON (융합 대비, 비트리거).

v1: 학파·대운·지장간·신살 슬롯 + 조율 가중 + 재현성 해시(확장 가능 규격).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from myeongni_lens_v1.advanced_payload import (
    build_input_digest_object,
    build_v1_payload,
    parse_advanced_input,
)
from myeongni_lens_v1.mkm_myeongni_math import compute_mkm_myeongni_math, compute_quant_profile_v0
from myeongni_lens_v1.fusion_bridge import (
    build_advanced_input_from_fusion,
    unwrap_fusion_payload,
)
from myeongni_lens_v1.repro import canonical_json_sha256
DEFAULT_EXPERIMENT = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_v1.calendar_stub_through_202604.jsonl"
DEFAULT_SAMPLE = ROOT / "data" / "myeongni" / "myeongni_16_state_experiment_v1.sample.jsonl"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "myeongni_independent_lens_latest.json"

ARTIFACT_SCHEMA = "myeongni_independent_lens_v0"
ENGINE_ID = "independent_lens_v0"
VERSION = "0.2.0"

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


def _recommended_advanced_and_provenance_path() -> tuple[dict[str, Any], str]:
    """MYEONGNI_FUSION_JSON 우선; 없으면 MYEONGNI_RECOMMENDED_BIRTH로 융합 즉시 계산."""
    env_fusion = os.environ.get("MYEONGNI_FUSION_JSON", "").strip()
    if env_fusion:
        p = Path(env_fusion)
        if p.is_file():
            try:
                fusion_wrap = json.loads(p.read_text(encoding="utf-8"))
                fus = unwrap_fusion_payload(fusion_wrap)
                if fus is not None:
                    adv = build_advanced_input_from_fusion(fus)
                    prov = adv.setdefault("provenance", {})
                    prov["recommended_mode"] = "env_MYEONGNI_FUSION_JSON"
                    return adv, str(p.resolve())
            except (OSError, json.JSONDecodeError, ValueError):
                pass

    from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

    birth_s = os.environ.get("MYEONGNI_RECOMMENDED_BIRTH", "2000,6,15,12").strip()
    parts = [x.strip() for x in birth_s.split(",") if x.strip()]
    if len(parts) != 4:
        parts = ["2000", "6", "15", "12"]
    y, mo, d, h = int(parts[0]), int(parts[1]), int(parts[2]), int(parts[3])
    sol = os.environ.get("MYEONGNI_RECOMMENDED_IS_SOLAR", "1").strip().lower()
    is_solar = sol in ("1", "true", "yes", "y")
    male = os.environ.get("MYEONGNI_RECOMMENDED_IS_MALE", "1").strip().lower()
    is_male = male in ("1", "true", "yes", "y")
    fus = MyeongriCompleteFusion().calculate_complete_fusion(
        y, mo, d, h, is_solar=is_solar, is_male=is_male
    )
    adv = build_advanced_input_from_fusion(fus)
    prov = adv.setdefault("provenance", {})
    prov["recommended_mode"] = "computed_from_MYEONGNI_RECOMMENDED_BIRTH"
    prov["recommended_birth_applied"] = {
        "year": y,
        "month": mo,
        "day": d,
        "hour": h,
        "is_solar": is_solar,
        "is_male": is_male,
    }
    return adv, ""


def _inject_coordinator_mkm_math_v0(payload: dict[str, Any]) -> None:
    """v0 스키마에도 v2가 읽는 `advanced.coordinator.mkm_myeongni_math`를 넣는다 (가능 시 status=ok)."""
    try:
        adv_raw, _p = _recommended_advanced_and_provenance_path()
    except Exception:
        adv_raw = None
    adv_parsed = parse_advanced_input(
        adv_raw if isinstance(adv_raw, dict) else None
    )
    math_result = compute_mkm_myeongni_math(adv_parsed)
    payload.setdefault("advanced", {})
    payload["advanced"].setdefault("coordinator", {})
    payload["advanced"]["coordinator"]["mkm_myeongni_math"] = math_result
    if str(math_result.get("status") or "") == "ok":
        payload["advanced"]["coordinator"]["mkm_myeongni_math_provenance"] = (
            "inject_v0_from_recommended_fusion_birth"
        )


def _inject_quant_block_v0(payload: dict[str, Any]) -> None:
    """오행·십성 정량 스냅샷 블록 (융합·관측용; A-track 트리거 아님)."""
    try:
        adv_raw, _ = _recommended_advanced_and_provenance_path()
    except Exception:
        adv_raw = None
    adv_parsed = parse_advanced_input(adv_raw if isinstance(adv_raw, dict) else None)
    payload["myeongni_b_track_quant_block_v0"] = compute_quant_profile_v0(adv_parsed)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Emit myeongni independent lens v0/v1 JSON from B-track experiment JSONL tail.",
    )
    ap.add_argument(
        "--emit-schema",
        choices=("v0", "v1"),
        default="v0",
        help="v0: legacy contract; v1: extended slots + reproducibility (default v0 for CI).",
    )
    ap.add_argument(
        "--advanced-input",
        type=Path,
        default=None,
        help="Optional JSON file myeongni_lens_advanced_input_v1 (pillars/dayun/sinsal/schools).",
    )
    ap.add_argument(
        "--advanced-from-fusion-json",
        type=Path,
        default=None,
        metavar="PATH",
        help="Wrap-or-fusion JSON → 내장 브리지로 advanced 입력 생성 (--advanced-input 과 동시 사용 불가).",
    )
    ap.add_argument(
        "--ruleset-id",
        type=str,
        default="",
        help="Override ruleset_id recorded under reproducibility.ruleset_id",
    )
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
    ap.add_argument(
        "--recommended",
        action="store_true",
        help="권장: --emit-schema v1 --allow-fallback; advanced는 MYEONGNI_FUSION_JSON 또는 생시 융합(환경변수, 기본 데모 생시).",
    )
    args = ap.parse_args()

    if args.recommended:
        args.emit_schema = "v1"
        args.allow_fallback = True

    advanced_doc: dict[str, Any] | None = None
    advanced_path_str = ""
    if args.advanced_input is not None and args.advanced_from_fusion_json is not None:
        print(
            "myeongni lens: use only one of --advanced-input or --advanced-from-fusion-json",
            file=sys.stderr,
        )
        return 2
    if args.advanced_from_fusion_json is not None:
        fusion_path = args.advanced_from_fusion_json
        if not fusion_path.is_file():
            print(f"myeongni lens: fusion file not found: {fusion_path}", file=sys.stderr)
            return 2
        try:
            fusion_wrap = json.loads(fusion_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"myeongni lens: failed to read fusion JSON: {e}", file=sys.stderr)
            return 2
        fus = unwrap_fusion_payload(fusion_wrap)
        if fus is None:
            print(
                "myeongni lens: could not unwrap fusion (need saju top-level or full_fusion_payload).",
                file=sys.stderr,
            )
            return 2
        advanced_doc = build_advanced_input_from_fusion(fus)
        advanced_path_str = str(fusion_path.resolve())
    elif args.advanced_input is not None:
        if args.advanced_input.is_file():
            try:
                advanced_doc = json.loads(args.advanced_input.read_text(encoding="utf-8"))
                advanced_path_str = str(args.advanced_input.resolve())
            except (OSError, json.JSONDecodeError):
                advanced_doc = None
    elif args.recommended:
        adv_r, path_r = _recommended_advanced_and_provenance_path()
        advanced_doc = adv_r
        advanced_path_str = path_r

    if advanced_doc is not None and args.emit_schema != "v1":
        print(
            "myeongni lens: --advanced-input / --advanced-from-fusion-json require --emit-schema v1",
            file=sys.stderr,
        )
        return 2

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
    if args.emit_schema == "v0":
        _inject_coordinator_mkm_math_v0(payload)
        _inject_quant_block_v0(payload)

    if args.emit_schema == "v1":
        adv = parse_advanced_input(advanced_doc)
        digest_src = build_input_digest_object(
            row_snapshot=dict(row),
            advanced_path=advanced_path_str or None,
            advanced_doc=advanced_doc if isinstance(advanced_doc, dict) else {},
            momentum_window=max(1, args.momentum_window),
        )
        ruleset = (args.ruleset_id or "").strip()
        payload = build_v1_payload(
            payload,
            advanced_block=adv,
            ruleset_id=ruleset,
            input_digest_src=digest_src,
        )
        payload["reproducibility"]["payload_content_digest_sha256"] = (
            "sha256:"
            + canonical_json_sha256(
                {k: payload[k] for k in ("scores", "advanced", "rules") if k in payload},
            )
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
