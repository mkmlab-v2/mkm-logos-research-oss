#!/usr/bin/env python3
"""Evaluate WTT session pre/post VA against EPB profile ([HYPO] · research_only)."""
from __future__ import annotations

import argparse
import copy
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = ROOT / "docs/final/schemas/warmth_trigger_profile_v1.example.json"
DEFAULT_DOSE = ROOT / "docs/final/schemas/warmth_content_dose_v1.example.json"
DEFAULT_OVERLAY = ROOT / "docs/final/artifacts/epb_sasang_overlay_rules_v1.json"
DEFAULT_OUT = ROOT / "reports/warmth_trigger_eval_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clip(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _apply_sasang_overlay(profile: dict[str, Any], overlay: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(profile)
    sasang = out.get("subject", {}).get("sasang_observed", "unknown")
    rules = overlay.get("rules", {})
    rule = rules.get(sasang) or rules.get("unknown", {})
    if not rule:
        return out

    sb = out["epb"]["sweet_band"]
    for k, delta in (rule.get("sweet_band_delta") or {}).items():
        if k in sb:
            sb[k] = _clip(float(sb[k]) + float(delta), -1.0, 1.0)

    th = out["epb"]["thresholds"]["t_high"]
    for k, delta in (rule.get("threshold_delta") or {}).items():
        if k in th:
            th[k] = _clip(float(th[k]) + float(delta), -1.0, 1.0)

    cap = rule.get("max_narrative_intensity_cap_0_1")
    if cap is not None:
        guards = out.setdefault("content_guards", {})
        current = float(guards.get("max_narrative_intensity_0_1", 1.0))
        guards["max_narrative_intensity_0_1"] = min(current, float(cap))

    return out


def _in_band(value: float, lo: float, hi: float) -> bool:
    return lo <= value <= hi


def classify_epb_outcome(
    *,
    pre_valence: float,
    pre_arousal: float,
    post_valence: float,
    post_arousal: float,
    profile: dict[str, Any],
    prior_overload: bool = False,
    pre_surprisal: float | None = None,
    post_surprisal: float | None = None,
) -> tuple[str, dict[str, Any]]:
    epb = profile["epb"]
    sweet = epb["sweet_band"]
    t_low = epb["thresholds"]["t_low"]
    t_high = epb["thresholds"]["t_high"]
    success = epb["success_criteria"]

    valence_delta = post_valence - pre_valence
    details: dict[str, Any] = {
        "pre_valence": pre_valence,
        "pre_arousal": pre_arousal,
        "post_valence": post_valence,
        "post_arousal": post_arousal,
        "valence_delta": round(valence_delta, 6),
    }

    hysteresis = profile.get("hysteresis_v1")
    if prior_overload and hysteresis:
        recovery = float(hysteresis["alpha_recovery_arousal"])
        if post_arousal > recovery:
            return "hysteresis_cooldown", {
                **details,
                "reason": "prior_overload_requires_arousal_below_recovery",
                "alpha_recovery_arousal": recovery,
            }

    if post_valence <= float(t_high["valence_floor"]) or post_arousal >= float(
        t_high["arousal_ceiling"]
    ):
        return "over", {**details, "reason": "t_high_breach"}

    if abs(valence_delta) < float(t_low["min_abs_valence_delta"]):
        return "under", {**details, "reason": "t_low_under_dose"}

    fep = profile.get("fep_proxy_v1")
    if fep and pre_surprisal is not None and post_surprisal is not None:
        min_delta = float(fep.get("min_surprisal_delta_for_hit", 0.1))
        surprisal_delta = pre_surprisal - post_surprisal
        details["surprisal_delta"] = round(surprisal_delta, 6)
        if surprisal_delta < min_delta:
            return "under", {**details, "reason": "fep_proxy_insufficient_surprisal_reduction"}

    if valence_delta < float(success["min_valence_delta"]):
        return "miss", {**details, "reason": "valence_delta_below_success"}

    if success.get("arousal_must_stay_in_sweet_band", True):
        if not _in_band(
            post_arousal,
            float(sweet["arousal_lo"]),
            float(sweet["arousal_hi"]),
        ):
            return "miss", {**details, "reason": "post_arousal_outside_sweet_band"}
        if not _in_band(
            post_valence,
            float(sweet["valence_lo"]),
            float(sweet["valence_hi"]),
        ):
            return "miss", {**details, "reason": "post_valence_outside_sweet_band"}

    return "hit", {**details, "reason": "epb_sweet_band_success"}


def check_dose_against_profile(dose: dict[str, Any], profile: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    d = dose.get("dose", {})
    guards = profile.get("content_guards", {})
    max_int = float(guards.get("max_narrative_intensity_0_1", 1.0))
    intensity = float(d.get("intensity_0_1", 0.0))
    if intensity > max_int:
        warnings.append("content_intensity_exceeds_profile_cap")

    if not guards.get("catharsis_allowed", True) and float(d.get("catharsis_0_1", 0)) > 0.3:
        warnings.append("catharsis_not_allowed_for_profile")

    exclude = set(guards.get("risk_tags_exclude") or [])
    for tag in d.get("risk_tags") or []:
        if tag in exclude:
            warnings.append(f"risk_tag_excluded:{tag}")

    if not d.get("recovery_arc_present", False):
        warnings.append("recovery_arc_missing")

    return warnings


def build_eval_report(
    *,
    profile: dict[str, Any],
    dose: dict[str, Any],
    session: dict[str, Any],
    overlay: dict[str, Any] | None,
) -> dict[str, Any]:
    effective_profile = profile
    if overlay:
        effective_profile = _apply_sasang_overlay(profile, overlay)

    pre = session["pre"]
    post = session["post"]
    outcome, outcome_details = classify_epb_outcome(
        pre_valence=float(pre["valence"]),
        pre_arousal=float(pre["arousal"]),
        post_valence=float(post["valence"]),
        post_arousal=float(post["arousal"]),
        profile=effective_profile,
        prior_overload=bool(session.get("prior_overload", False)),
        pre_surprisal=session.get("pre_surprisal_0_1"),
        post_surprisal=session.get("post_surprisal_0_1"),
    )

    dose_warnings = check_dose_against_profile(dose, effective_profile)
    recommended_arm = "standard"
    if outcome == "over" and effective_profile.get("content_guards", {}).get(
        "warm_only_fallback_on_overload", True
    ):
        recommended_arm = "warm_only_cooldown"
    elif outcome in ("under", "miss"):
        recommended_arm = "re_dose_or_lower_intensity"
    elif outcome == "hysteresis_cooldown":
        recommended_arm = "warm_only_until_recovery"

    return {
        "schema": "warmth_trigger_eval_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "research_only": True,
        "hypothesis_class": "HYPO",
        "disclaimer_ko": (
            "본 평가는 의학적 진단·치료 효능을 보장하지 않는 B-track 웰니스 연구 파일럿입니다."
        ),
        "session_id": session.get("session_id", "unknown"),
        "content_id": dose.get("content_id"),
        "profile_version": effective_profile.get("profile_version"),
        "dose_version": dose.get("dose_version"),
        "outcome": outcome,
        "outcome_details": outcome_details,
        "dose_warnings": dose_warnings,
        "recommended_arm": recommended_arm,
        "sasang_observed": effective_profile.get("subject", {}).get("sasang_observed"),
        "overlay_applied": overlay is not None,
        "metaphor_notices": [
            "landauer_and_fep_are_self_report_proxies_not_brain_measurement",
            "epb_not_clinical_treatment_endpoint",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--profile-json", type=Path, default=DEFAULT_PROFILE)
    ap.add_argument("--dose-json", type=Path, default=DEFAULT_DOSE)
    ap.add_argument("--overlay-json", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--no-overlay", action="store_true")
    ap.add_argument(
        "--session-json",
        type=Path,
        help="Session with pre/post valence, arousal, optional surprisal fields.",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    profile = _load_json(args.profile_json)
    dose = _load_json(args.dose_json)
    overlay = None if args.no_overlay else _load_json(args.overlay_json)

    if args.session_json:
        session = _load_json(args.session_json)
    else:
        session = {
            "session_id": "demo_session_hit",
            "pre": {"valence": -0.1, "arousal": -0.2},
            "post": {"valence": 0.25, "arousal": 0.05},
            "pre_surprisal_0_1": 0.7,
            "post_surprisal_0_1": 0.45,
            "prior_overload": False,
        }

    report = build_eval_report(
        profile=profile, dose=dose, session=session, overlay=overlay
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "outcome": report["outcome"], "out": str(args.out.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
