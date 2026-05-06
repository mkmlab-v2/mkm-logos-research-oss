#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_LENS = ART / "myeongni_independent_lens_latest.json"
DEFAULT_WEATHER = ART / "general_prophecy_explainability_quality_v1_latest.json"
DEFAULT_OUT = ART / "mkm_myeongni_response_v2_calibration_latest.json"

PROFILE_PRESETS: dict[str, dict[str, float]] = {
    "conservative": {
        "hold_confidence_cut": 0.46,
        "reduce_direction_cut": 0.62,
        "reduce_confidence_cut": 0.72,
        "failed_check_penalty": 0.05,
    },
    "balanced": {
        "hold_confidence_cut": 0.42,
        "reduce_direction_cut": 0.55,
        "reduce_confidence_cut": 0.66,
        "failed_check_penalty": 0.03,
    },
    "attack": {
        "hold_confidence_cut": 0.35,
        "reduce_direction_cut": 0.35,
        "reduce_confidence_cut": 0.50,
        "failed_check_penalty": 0.01,
    },
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _extract_core(lens: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    failed: list[str] = []
    scores = lens.get("scores") if isinstance(lens.get("scores"), dict) else {}
    adv = lens.get("advanced") if isinstance(lens.get("advanced"), dict) else {}
    coordinator = adv.get("coordinator") if isinstance(adv.get("coordinator"), dict) else {}
    math = coordinator.get("mkm_myeongni_math") if isinstance(coordinator.get("mkm_myeongni_math"), dict) else {}

    d_core = _f(math.get("arbitrated_direction_score"), _f(scores.get("direction_score"), 0.0))
    c_core = _f(math.get("arbitrated_confidence"), _f(scores.get("confidence"), 0.5))
    ten = _f(math.get("ten_god_balance"), 0.0)
    jij = _f(math.get("jijangan_pressure"), 0.0)
    sdi = _f(math.get("school_disagreement_index"), 0.0)
    if str(math.get("status") or "") != "ok":
        failed.append("mkm_myeongni_math_not_ok")

    return (
        {
            "direction_core": round(_clip(d_core, -1.0, 1.0), 6),
            "confidence_core": round(_clip(c_core, 0.0, 1.0), 6),
            "ten_god_balance": round(ten, 6),
            "jijangan_pressure": round(max(0.0, jij), 6),
            "school_disagreement_index": round(_clip(sdi, 0.0, 1.0), 6),
        },
        failed,
    )


def _weather_term(weather: dict[str, Any], failed: list[str]) -> tuple[float, list[str]]:
    summary = weather.get("summary") if isinstance(weather.get("summary"), dict) else {}
    raw_direct = summary.get("direct_match_rate")
    if raw_direct is None:
        raw_direct = summary.get("coverage_rate")
    direct = _f(raw_direct, -1.0)
    repro = _f(summary.get("reproducible_evidence_rate"), -1.0)
    if direct < 0 or repro < 0:
        failed.append("weather_quality_missing")
        return (0.0, failed)
    term = 0.08 * (direct - 0.5) + 0.06 * (repro - 0.8)
    return (round(_clip(term, -0.2, 0.2), 6), failed)


def _decision(
    direction: float,
    confidence_adj: float,
    failed: list[str],
    *,
    hold_confidence_cut: float,
    reduce_direction_cut: float,
    reduce_confidence_cut: float,
) -> tuple[str, str]:
    if failed:
        return ("HOLD", "Coordinator failed checks present.")
    if confidence_adj < hold_confidence_cut:
        return ("HOLD", "Low adjusted confidence.")
    if abs(direction) >= reduce_direction_cut and confidence_adj >= reduce_confidence_cut:
        return ("REDUCE", "Strong directional signal with calibrated confidence.")
    return ("WATCH", "Moderate confidence; keep observation posture.")


def _frange(start: float, stop: float, step: float) -> list[float]:
    vals: list[float] = []
    x = start
    while x <= stop + 1e-9:
        vals.append(round(x, 6))
        x += step
    return vals


def _build_replay(core: dict[str, Any], weather_term: float) -> list[dict[str, float]]:
    base_d = float(core.get("direction_core") or 0.0)
    base_c = float(core.get("confidence_core") or 0.5)
    scenarios: list[dict[str, float]] = []
    d_offsets = [-0.25, -0.1, 0.0, 0.1, 0.25]
    c_offsets = [-0.15, -0.05, 0.0, 0.05, 0.15]
    for do in d_offsets:
        for co in c_offsets:
            scenarios.append(
                {
                    "direction": _clip(base_d + do, -1.0, 1.0),
                    "confidence_adjusted": _clip(base_c + weather_term + co, 0.0, 1.0),
                }
            )
    return scenarios


def _evaluate_profile(
    replay: list[dict[str, float]],
    profile_name: str,
    *,
    failed_count: int,
) -> dict[str, Any]:
    cfg = PROFILE_PRESETS[profile_name]
    counts = {"HOLD": 0, "WATCH": 0, "REDUCE": 0}
    for s in replay:
        c_adj = _clip(
            float(s["confidence_adjusted"]) - (float(cfg["failed_check_penalty"]) * float(failed_count)),
            0.0,
            1.0,
        )
        dec, _ = _decision(
            float(s["direction"]),
            c_adj,
            [],
            hold_confidence_cut=float(cfg["hold_confidence_cut"]),
            reduce_direction_cut=float(cfg["reduce_direction_cut"]),
            reduce_confidence_cut=float(cfg["reduce_confidence_cut"]),
        )
        counts[dec] += 1
    n = max(1, len(replay))
    return {
        "profile": profile_name,
        "hold_confidence_cut": float(cfg["hold_confidence_cut"]),
        "reduce_direction_cut": float(cfg["reduce_direction_cut"]),
        "reduce_confidence_cut": float(cfg["reduce_confidence_cut"]),
        "failed_check_penalty": float(cfg["failed_check_penalty"]),
        "hold_ratio": round(counts["HOLD"] / n, 6),
        "watch_ratio": round(counts["WATCH"] / n, 6),
        "reduce_ratio": round(counts["REDUCE"] / n, 6),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Calibrate MKM myeongni v2 decision thresholds with replay grid.")
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--weather-quality-json", type=Path, default=DEFAULT_WEATHER)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    lens = _read_json(args.lens_json if args.lens_json.is_absolute() else ROOT / args.lens_json)
    weather = _read_json(args.weather_quality_json if args.weather_quality_json.is_absolute() else ROOT / args.weather_quality_json)
    core, failed = _extract_core(lens)
    weather_term, failed2 = _weather_term(weather, list(failed))
    failed_count = len(failed2)

    replay = _build_replay(core, weather_term)
    holds_target_max = 0.35
    reduces_target_max = 0.40

    best: dict[str, Any] | None = None
    hold_cuts = _frange(0.36, 0.46, 0.01)
    reduce_d_cuts = _frange(0.45, 0.60, 0.01)
    reduce_c_cuts = _frange(0.58, 0.72, 0.01)

    for h in hold_cuts:
        for rd in reduce_d_cuts:
            for rc in reduce_c_cuts:
                counts = {"HOLD": 0, "WATCH": 0, "REDUCE": 0}
                for s in replay:
                    dec, _ = _decision(
                        float(s["direction"]),
                        float(s["confidence_adjusted"]),
                        [],
                        hold_confidence_cut=h,
                        reduce_direction_cut=rd,
                        reduce_confidence_cut=rc,
                    )
                    counts[dec] += 1
                n = max(1, len(replay))
                hold_ratio = counts["HOLD"] / n
                reduce_ratio = counts["REDUCE"] / n
                penalty = 0.0
                if hold_ratio > holds_target_max:
                    penalty += (hold_ratio - holds_target_max) * 10.0
                if reduce_ratio > reduces_target_max:
                    penalty += (reduce_ratio - reduces_target_max) * 5.0
                # Prefer lower hold while avoiding over-aggressive reduce
                score = penalty + (hold_ratio * 1.0) + (abs(reduce_ratio - 0.25) * 0.6)
                cand = {
                    "hold_confidence_cut": h,
                    "reduce_direction_cut": rd,
                    "reduce_confidence_cut": rc,
                    "hold_ratio": round(hold_ratio, 6),
                    "watch_ratio": round(counts["WATCH"] / n, 6),
                    "reduce_ratio": round(reduce_ratio, 6),
                    "score": round(score, 6),
                }
                if best is None or cand["score"] < best["score"]:
                    best = cand

    assert best is not None
    out = {
        "schema": "mkm_myeongni_response_v2_calibration_v1",
        "generated_at_utc": _now(),
        "input": {
            "lens_json": str(args.lens_json),
            "weather_quality_json": str(args.weather_quality_json),
            "failed_check_count_at_source": failed_count,
            "weather_calibration_term_at_source": weather_term,
        },
        "replay": {"scenario_count": len(replay)},
        "recommended": best,
        "preset_profiles": [
            _evaluate_profile(replay, "conservative", failed_count=failed_count),
            _evaluate_profile(replay, "balanced", failed_count=failed_count),
            _evaluate_profile(replay, "attack", failed_count=failed_count),
        ],
        "policy": {
            "direction_override_allowed": False,
            "research_only": True,
            "auto_apply": False,
            "human_signoff_required": True,
        },
    }
    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "recommended": best}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
