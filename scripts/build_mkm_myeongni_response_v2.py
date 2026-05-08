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
DEFAULT_LENS_FALLBACK = ART / "independent_lens_latest.json"
DEFAULT_LENS_STUB_FALLBACK = ART / "independent_lens_fusion_stub_latest.json"
DEFAULT_WEATHER = ART / "general_prophecy_explainability_quality_v1_latest.json"
DEFAULT_OUT = ART / "mkm_myeongni_response_v2_latest.json"

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


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _f(v: Any, d: float = 0.0) -> float:
    return float(v) if isinstance(v, (int, float)) else d


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


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
    # confidence-only calibration: weather improves trust signal, not direction
    term = 0.08 * (direct - 0.5) + 0.06 * (repro - 0.8)
    term = _clip(term, -0.2, 0.2)
    return (round(term, 6), failed)


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


def _profile_thresholds(profile: str) -> dict[str, float]:
    return dict(PROFILE_PRESETS.get(profile, PROFILE_PRESETS["balanced"]))


def main() -> int:
    ap = argparse.ArgumentParser(description="Build MKM Myeongni response v2 (core + coordinator).")
    ap.add_argument("--lens-json", type=Path, default=DEFAULT_LENS)
    ap.add_argument("--weather-quality-json", type=Path, default=DEFAULT_WEATHER)
    ap.add_argument("--profile", choices=("conservative", "balanced", "attack"), default="balanced")
    ap.add_argument("--track", choices=("A", "B"), default="B")
    ap.add_argument("--hold-confidence-cut", type=float, default=None)
    ap.add_argument("--reduce-direction-cut", type=float, default=None)
    ap.add_argument("--reduce-confidence-cut", type=float, default=None)
    ap.add_argument("--failed-check-penalty", type=float, default=None)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    profile_cfg = _profile_thresholds(args.profile)
    hold_cut = float(args.hold_confidence_cut) if args.hold_confidence_cut is not None else profile_cfg["hold_confidence_cut"]
    reduce_d_cut = (
        float(args.reduce_direction_cut) if args.reduce_direction_cut is not None else profile_cfg["reduce_direction_cut"]
    )
    reduce_c_cut = (
        float(args.reduce_confidence_cut) if args.reduce_confidence_cut is not None else profile_cfg["reduce_confidence_cut"]
    )
    failed_penalty = (
        float(args.failed_check_penalty) if args.failed_check_penalty is not None else profile_cfg["failed_check_penalty"]
    )

    lens_path = args.lens_json if args.lens_json.is_absolute() else ROOT / args.lens_json
    if not lens_path.is_file() and lens_path == DEFAULT_LENS:
        if DEFAULT_LENS_FALLBACK.is_file():
            lens_path = DEFAULT_LENS_FALLBACK
        elif DEFAULT_LENS_STUB_FALLBACK.is_file():
            lens_path = DEFAULT_LENS_STUB_FALLBACK
    if not lens_path.is_file():
        raise SystemExit(f"missing lens json: {lens_path}")
    lens = _read_json(lens_path)
    weather = _read_json(args.weather_quality_json if args.weather_quality_json.is_absolute() else ROOT / args.weather_quality_json)

    core, failed = _extract_core(lens)
    w_term, failed = _weather_term(weather, failed)
    c_adj = _clip(core["confidence_core"] + w_term - (failed_penalty * len(failed)), 0.0, 1.0)
    dec, reason = _decision(
        core["direction_core"],
        c_adj,
        failed,
        hold_confidence_cut=hold_cut,
        reduce_direction_cut=reduce_d_cut,
        reduce_confidence_cut=reduce_c_cut,
    )

    out = {
        "schema": "mkm_myeongni_response_v2",
        "generated_at_utc": _now(),
        "track": args.track,
        "core_layer": core,
        "coordinator_layer": {
            "direction_override_allowed": False,
            "weather_calibration_term": round(w_term, 6),
            "confidence_adjusted": round(c_adj, 6),
            "failed_check_keys": failed,
        },
        "final_action": {"decision": dec, "reason": reason},
        "governance": {
            "research_only": args.track == "B",
            "human_signoff_required": True,
        },
        "calibration": {
            "profile": args.profile,
            "hold_confidence_cut": round(hold_cut, 6),
            "reduce_direction_cut": round(reduce_d_cut, 6),
            "reduce_confidence_cut": round(reduce_c_cut, 6),
            "failed_check_penalty": round(failed_penalty, 6),
        },
    }

    out_path = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "decision": dec, "lens_source": str(lens_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
