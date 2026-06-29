#!/usr/bin/env python3
"""KOSPI shock conditional attach operator policy (B-track · advisory only).

Shock-day ON / calm-day OFF posture from disk SSOT — not Track A · not live routing.

  py scripts/build_kospi_shock_conditional_attach_operator_policy_v1.py
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
OUT_JSON = ART / "kospi_shock_conditional_attach_operator_policy_v1_latest.json"
OUT_MD = ART / "kospi_shock_conditional_attach_operator_policy_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return {}
    return raw if isinstance(raw, dict) else {}


def _latest_kospi_prior_return_pct(kospi_csv: Path) -> float | None:
    if not kospi_csv.is_file():
        return None
    try:
        import csv

        rows: list[dict[str, str]] = []
        with kospi_csv.open(encoding="utf-8-sig", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                rows.append(row)
        if len(rows) < 2:
            return None
        for key in ("daily_return", "return", "Daily Return"):
            if key in rows[-1]:
                return float(rows[-1][key]) * (100.0 if abs(float(rows[-1][key])) <= 1.0 else 1.0)
        if "Close" in rows[-1] and "Close" in rows[-2]:
            prev = float(rows[-2]["Close"])
            cur = float(rows[-1]["Close"])
            if prev:
                return (cur / prev - 1.0) * 100.0
    except (OSError, ValueError, KeyError, csv.Error):
        return None
    return None


def _evaluate_shock_triggers(
    *,
    conditional: dict[str, Any],
    conflict: dict[str, Any],
    overnight: dict[str, Any],
    prior_kospi_return_pct: float | None,
    prior_threshold_pct: float,
) -> dict[str, Any]:
    shock_bps = float(conditional.get("shock_move_bps_threshold") or 100.0)
    inputs = conflict.get("inputs_snapshot") if isinstance(conflict.get("inputs_snapshot"), dict) else {}
    overnight_block = inputs.get("overnight") if isinstance(inputs.get("overnight"), dict) else {}
    hypo = inputs.get("hypothesis") if isinstance(inputs.get("hypothesis"), dict) else {}

    shock_overnight = bool(overnight_block.get("shock_overnight"))
    recent_abs = hypo.get("recent_abs_return_mean")
    try:
        shock_vol = float(recent_abs or 0.0) >= 0.025
    except (TypeError, ValueError):
        shock_vol = False

    prior_shock = (
        prior_kospi_return_pct is not None and prior_kospi_return_pct <= prior_threshold_pct
    )
    regime = str(conflict.get("regime") or "normal")
    shock_regime = regime == "shock" or shock_overnight or shock_vol or prior_shock

    triggers: list[dict[str, Any]] = [
        {
            "id": "science_shock_move_bps",
            "threshold": f"|forward|>={shock_bps}bps (holdout label)",
            "active": shock_regime,
            "source": "science_core_conditional_attach_research_v1",
        },
        {
            "id": "conflict_shock_overnight",
            "threshold": "risk_off_overnight + index move >=3%",
            "active": shock_overnight,
            "source": "build_lens_conflict_day_decision_snapshot_v1",
        },
        {
            "id": "conflict_shock_vol",
            "threshold": "recent_abs_return_mean>=2.5%",
            "active": shock_vol,
            "source": "build_lens_conflict_day_decision_snapshot_v1",
        },
        {
            "id": "prior_kospi_day_shock",
            "threshold": f"prior completed daily return<={prior_threshold_pct}%",
            "active": prior_shock,
            "observed_pct": prior_kospi_return_pct,
            "source": "prophecy_overlay_prior_threshold_recommended_v1",
        },
    ]

    return {
        "shock_regime": shock_regime,
        "regime_label": "shock" if shock_regime else "calm",
        "triggers": triggers,
        "prior_kospi_return_pct": prior_kospi_return_pct,
    }


def build_policy(root: Path | None = None) -> dict[str, Any]:
    ws = (root or ROOT).resolve()
    art = ws / "docs" / "final" / "artifacts"

    conditional = _read_json(art / "science_core_conditional_attach_research_v1_latest.json")
    signoff = _read_json(art / "science_core_research_attach_signoff_v1_latest.json")
    governance = _read_json(art / "science_core_governance_bundle_v1_latest.json")
    conflict = _read_json(art / "lens_conflict_day_decision_snapshot_v1_latest.json")
    overnight = _read_json(art / "global_market_overnight_signals_v1_latest.json")
    prior_thr_doc = _read_json(art / "prophecy_overlay_prior_threshold_recommended_latest.json")
    morning = _read_json(art / "internal_kospi_morning_brief_onepager_latest.json")

    prior_threshold = float(prior_thr_doc.get("recommended_prior_return_threshold") or -0.06) * 100.0
    kospi_csv = ws / "research" / "market_data" / "kospi_daily_external_yf.csv"
    prior_kospi_pct = _latest_kospi_prior_return_pct(kospi_csv)

    shock_eval = _evaluate_shock_triggers(
        conditional=conditional,
        conflict=conflict,
        overnight=overnight,
        prior_kospi_return_pct=prior_kospi_pct,
        prior_threshold_pct=prior_threshold,
    )

    kospi_slice = (
        conditional.get("instrument_slices", {}).get("kospi", {})
        if isinstance(conditional.get("instrument_slices"), dict)
        else {}
    )
    shock_subset = (
        kospi_slice.get("shock_subset_short_1d", {})
        if isinstance(kospi_slice.get("shock_subset_short_1d"), dict)
        else {}
    )
    sasang_shock = shock_subset.get("science_plus_sasang", {})
    core_shock = shock_subset.get("science_core", {})

    attach_mode = "ON" if shock_eval["shock_regime"] else "OFF"
    conflict_action = str(conflict.get("final_action") or "HOLD")
    conflict_posture = str(conflict.get("operator_posture") or "neutral_hold")

    if attach_mode == "ON":
        operator_posture = conflict_posture if conflict_action in {"REDUCE", "WATCH"} else "shock_attach_watch"
        today_action = conflict_action if conflict_action in {"REDUCE", "WATCH", "HOLD"} else "WATCH"
        attach_lane = "science_plus_sasang"
        attach_note_ko = (
            "쇼크 구간: KOSPI short_1d market_dynamics_quant attach ON "
            "(science_core+OHLCV sasang proxy — NOT human 사상/명리/성경 D-type). "
            "BTC attach OFF. 신규매수 금지·비중 축소 검토."
        )
    else:
        operator_posture = (
            conflict_posture if conflict_action in {"REDUCE", "WATCH"} else "calm_default_off"
        )
        if conflict_action in {"REDUCE", "WATCH", "HOLD"}:
            today_action = conflict_action
        else:
            today_action = str(morning.get("today_action") or "HOLD")
        attach_lane = "science_core_only"
        attach_note_ko = "평시: sasang attach OFF. conflict-day posture만 참고."

    evidence_holdout = {
        "kospi_shock_n": kospi_slice.get("n_shock_days"),
        "science_core_soft_shock": (core_shock or {}).get("soft_hit_rate"),
        "science_plus_sasang_soft_shock": (sasang_shock or {}).get("soft_hit_rate"),
        "uplift_pp_shock": (sasang_shock or {}).get("uplift_vs_science_pp"),
        "holdout_window": kospi_slice.get("holdout_window"),
    }

    return {
        "schema": "kospi_shock_conditional_attach_operator_policy_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "audience": "internal_operator",
        "boundary_ack": (
            "[HYPO] Advisory posture only — not Track A · not live trading · not auto order. "
            "Logos [NON_GATING]. Human execution on broker/VPS rules remains separate."
        ),
        "policy_id": "kospi_shock_on_calm_off_v1",
        "attach_switch": {
            "mode": attach_mode,
            "regime_label": shock_eval["regime_label"],
            "kospi_lane_when_on": "market_dynamics_quant",
            "kospi_lane_when_off": "science_core_only",
            "kospi_lane_note_ko": (
                "ON=science_core+market_sasang OHLCV proxy (NOT human 사상/명리/성경 D-type prediction)"
            ),
            "btc_lane": "observe_only_attach_off",
            "horizon": "short_1d_only",
        },
        "today_evaluation": {
            "today_action": today_action,
            "operator_posture": operator_posture,
            "conflict_day_final_action": conflict_action,
            "conflict_day_posture": conflict_posture,
            "attach_note_ko": attach_note_ko,
            "shock_triggers": shock_eval["triggers"],
            "prior_kospi_return_pct": prior_kospi_pct,
        },
        "rules": {
            "shock_on_conditions_any": [
                "conflict_regime=shock OR shock_overnight OR shock_vol OR prior_kospi<=-6%",
                "instrument=KOSPI only for sasang attach",
            ],
            "calm_off_default": [
                "no shock trigger → sasang attach OFF",
                "use conflict-day + morning brief for posture only",
            ],
            "btc_always_off": [
                "BTC shock subset uplift negative (-7.5pp holdout) — attach OFF",
                "science_core observe_only per instrument_matrix",
            ],
            "forbidden": [
                "auto order / Track A merge / prophecy→live trigger",
                "economic edge public claim",
                "Logos as gating trigger",
            ],
        },
        "operator_checklist": [
            "confirm shock_triggers from latest artifacts (freshness)",
            "if attach ON: KOSPI only — no new buys, review reduce/watch",
            "if attach OFF: calm — hold unless conflict-day REDUCE/WATCH",
            "BTC: never enable shock attach from this policy",
            "orders: separate VPS/human gate — this policy is posture only",
        ],
        "holdout_evidence": evidence_holdout,
        "promotion_status": {
            "composite_research_attach_approved": signoff.get("composite_research_attach_approved"),
            "track_a_promotion_approved": signoff.get("track_a_promotion_approved"),
            "live_trading_approved": signoff.get("live_trading_approved"),
            "track_a_ready": (signoff.get("gates_snapshot") or {}).get("track_a_ready"),
            "recommended_lane": signoff.get("recommended_lane"),
            "final_action_research": (conditional.get("final_action") or {}).get("action_id"),
            "promotion_verdict_ko": (
                "B-track operator/advisory tier 채택 가능. Track A·live auto 승격 불가(현재 HOLD)."
            ),
        },
        "evidence_paths": [
            "docs/final/artifacts/science_core_conditional_attach_research_v1_latest.json",
            "docs/final/artifacts/science_core_research_attach_signoff_v1_latest.json",
            "docs/final/artifacts/lens_conflict_day_decision_snapshot_v1_latest.json",
            "docs/final/artifacts/internal_kospi_morning_brief_onepager_latest.json",
            "docs/final/artifacts/science_core_instrument_matrix_v1_latest.json",
        ],
        "repro_command": "py scripts/build_kospi_shock_conditional_attach_operator_policy_v1.py",
        "governance_snapshot": {
            "kospi_holdout_uplift_soft": (governance.get("holdout") or {}).get("kospi_holdout_uplift_soft"),
            "always_attach_recommended": (governance.get("holdout") or {}).get("always_attach_recommended"),
        },
    }


def _render_md(payload: dict[str, Any]) -> str:
    te = payload.get("today_evaluation") or {}
    attach = payload.get("attach_switch") or {}
    holdout = payload.get("holdout_evidence") or {}
    promo = payload.get("promotion_status") or {}

    lines = [
        "# KOSPI Shock Conditional Attach — Operator Policy (1 Page)",
        "",
        f"- schema: `{payload.get('schema')}`",
        f"- generated_at_utc: `{payload.get('generated_at_utc')}`",
        f"- audience: `{payload.get('audience')}`",
        f"- boundary: `{payload.get('boundary_ack')}`",
        "",
        "## A) Today Switch",
        "",
        f"- attach_mode: **`{attach.get('mode')}`** ({attach.get('regime_label')})",
        f"- today_action: **`{te.get('today_action')}`**",
        f"- operator_posture: `{te.get('operator_posture')}`",
        f"- KOSPI lane: ON=`{attach.get('kospi_lane_when_on')}` · OFF=`{attach.get('kospi_lane_when_off')}`",
        f"- lane note: {attach.get('kospi_lane_note_ko')}",
        f"- BTC: **`{attach.get('btc_lane')}`** (always attach OFF)",
        "",
        "## B) Shock Triggers (any → KOSPI attach ON)",
        "",
    ]
    for row in te.get("shock_triggers") or []:
        flag = "YES" if row.get("active") else "no"
        obs = row.get("observed_pct")
        extra = f" · observed={obs}%" if obs is not None else ""
        lines.append(f"- [{flag}] `{row.get('id')}` — {row.get('threshold')}{extra}")

    lines.extend(
        [
            "",
            "## C) Calm Default (all off → attach OFF)",
            "",
            "- sasang attach OFF; conflict-day + morning brief posture only",
            "- no auto order; no Track A merge",
            "",
            "## D) Operator Checklist",
            "",
        ]
    )
    for item in payload.get("operator_checklist") or []:
        lines.append(f"- [ ] {item}")

    lines.extend(
        [
            "",
            "## E) Holdout Evidence (research · small n)",
            "",
            f"- KOSPI shock days (holdout): n={holdout.get('kospi_shock_n')}",
            f"- science_core soft (shock): {holdout.get('science_core_soft_shock')}",
            f"- science+sasang soft (shock): {holdout.get('science_plus_sasang_soft_shock')}",
            f"- uplift pp (shock): {holdout.get('uplift_pp_shock')}",
            "",
            "## F) Promotion",
            "",
            f"- composite_research_attach_approved: `{promo.get('composite_research_attach_approved')}`",
            f"- track_a / live: `{promo.get('track_a_promotion_approved')}` / `{promo.get('live_trading_approved')}`",
            f"- verdict: {promo.get('promotion_verdict_ko')}",
            "",
            "## G) Evidence Paths",
            "",
        ]
    )
    for path in payload.get("evidence_paths") or []:
        lines.append(f"- `{path}`")
    lines.extend(
        [
            "",
            f"Confidence: derived from shock triggers + conflict-day + holdout research slice.",
            f"Evidence: {', '.join(payload.get('evidence_paths') or [])}",
            "Uncertainty trigger: holdout n<30 · June calendar miss · BTC attach diverges — extend holdout before policy hardening.",
            "",
            f"Repro: `{payload.get('repro_command')}`",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> int:
    payload = build_policy()
    ART.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_MD.write_text(_render_md(payload), encoding="utf-8")
    print(f"WROTE: {OUT_JSON}")
    print(f"WROTE: {OUT_MD}")
    print(f"attach_mode={payload['attach_switch']['mode']} today_action={payload['today_evaluation']['today_action']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
