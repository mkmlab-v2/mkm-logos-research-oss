#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""[HYPO] 3-arm equal-weight sandbox: baseline / cultural-equal / cultural+science-equal."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import _read_json  # noqa: E402
from scripts.kospi_june2026_multilens_blend_v1 import default_weights_v2, load_static_lenses  # noqa: E402
from scripts.run_kospi_multilens_blend_backtest_v1 import (  # noqa: E402
    EVOLUTION_RULES,
    KOSPI_CSV,
    _load_closes,
    _load_panel,
    _normalize_weights,
    run_backtest,
)

BTC_CSV = ROOT / "research/market_data/btc_daily_external_yf.csv"
KOSPI_PANEL = ROOT / "reports/btrack_session_myeongni_panel_252d_v1.csv"
BTC_PANEL = ROOT / "reports/btrack_session_myeongni_panel_full_window_v1.csv"
DEFAULT_OUT = ROOT / "reports/multilens_equal_weight_sandbox_3arm_v1_latest.json"


def _utc_now() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sandbox_3arm_catalog(instrument: str) -> dict[str, dict[str, Any]]:
    v2_keys = list(default_weights_v2().keys())

    def z(**patch: float) -> dict[str, float]:
        base = {k: 0.0 for k in v2_keys}
        base.update(patch)
        return _normalize_weights(base, v2_keys)

    if instrument == "btc":
        arm_a_patch = {"session_myeongni": 0.55, "momentum_overlay": 0.45}
        arm_a_note = "instrument best: v2_session_momentum_only_4ai_current (logos 0)"
    else:
        arm_a_patch = {
            "session_myeongni": 0.30,
            "myeongni_independent": 0.22,
            "sasang": 0.24,
            "macro": 0.24,
        }
        arm_a_note = "instrument best: v2_default_4ai_current (logos 0)"

    third = round(1.0 / 3.0, 4)
    sixth = round(1.0 / 6.0, 4)

    return {
        "sandbox_arm_a_baseline": {
            "profile": "v2_multilens",
            "weights": z(**arm_a_patch),
            "note": arm_a_note,
        },
        "sandbox_arm_b_equal_cultural_3": {
            "profile": "v2_multilens",
            "weights": z(
                myeongni_independent=third,
                sasang=third,
                logos_non_gating=third,
            ),
            "note": "myeongni+sasang+logos 1/3 each; science channels 0; logos [NON_GATING] vote only",
        },
        "sandbox_arm_c_equal_cultural_plus_science": {
            "profile": "v2_multilens",
            "weights": z(
                myeongni_independent=sixth,
                sasang=sixth,
                logos_non_gating=sixth,
                macro=sixth,
                momentum_overlay=sixth,
                ensemble_kospi_causal=sixth,
            ),
            "note": (
                "50% cultural (1/6 each) + 50% science proxy: macro + momentum(price) + "
                "ensemble_kospi_causal(news/cross); price/news not native v2 keys"
            ),
        },
    }


def _strip_4ai_suffix(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for r in rows:
        row = dict(r)
        vid = str(row.get("variant_id") or "")
        if vid.endswith("_4ai_current"):
            row["variant_id"] = vid[: -len("_4ai_current")]
        out.append(row)
    return out


def _evaluate_arms(arms: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = {str(a.get("variant_id")): a for a in arms}
    a = by_id.get("sandbox_arm_a_baseline") or {}
    c = by_id.get("sandbox_arm_c_equal_cultural_plus_science") or {}
    b = by_id.get("sandbox_arm_b_equal_cultural_3") or {}
    ma = a.get("metrics") or {}
    mc = c.get("metrics") or {}
    mb = b.get("metrics") or {}
    dir_a = ma.get("directional_hit_rate")
    dir_c = mc.get("directional_hit_rate")
    dir_b = mb.get("directional_hit_rate")
    delta_c = round(float(dir_c) - float(dir_a), 4) if dir_a is not None and dir_c is not None else None
    delta_b = round(float(dir_b) - float(dir_a), 4) if dir_a is not None and dir_b is not None else None
    neut_c = int(mc.get("neutral_draw") or 0)
    neut_a = int(ma.get("neutral_draw") or 0)
    neut_spike = neut_c > neut_a + max(3, int((ma.get("n_scored") or 0) * 0.05))
    research_pass = (
        delta_c is not None
        and delta_c >= 0.03
        and dir_c is not None
        and not neut_spike
    )
    return {
        "delta_directional_arm_c_minus_a": delta_c,
        "delta_directional_arm_b_minus_a": delta_b,
        "neutral_spike_arm_c_vs_a": neut_spike,
        "research_promotion_candidate": research_pass,
        "research_promotion_note_ko": (
            "arm_c +3pp 이상且neutral 급증 없음 시에만 'Logos 균등 격상 방향 이득' 후속 연구"
            if research_pass
            else "Logos 균등+과학 50/50 arm_c는 baseline 대비 승격 후보 아님 — Logos는 압축/해설 축 유지"
        ),
    }


def run_instrument(
    *,
    instrument: str,
    panel_csv: Path,
    ohlcv_csv: Path,
    date_from: str,
    date_to: str,
    rules: dict[str, Any],
) -> dict[str, Any]:
    panel = _load_panel(panel_csv)
    closes = _load_closes(ohlcv_csv)
    catalog = sandbox_3arm_catalog(instrument)
    doc = run_backtest(
        panel_by_date=panel,
        closes=closes,
        date_from=date_from,
        date_to=date_to,
        rules=rules,
        catalog=catalog,
        four_ai_modes=("current",),
    )
    arms = _strip_4ai_suffix(list(doc.get("variants") or []))
    static = load_static_lenses()
    logos = static.get("logos") if isinstance(static.get("logos"), dict) else {}
    return {
        "instrument": instrument,
        "window": doc.get("window"),
        "ohlcv_csv": str(ohlcv_csv),
        "panel_csv": str(panel_csv),
        "logos_snapshot": {
            "direction": logos.get("direction"),
            "score": logos.get("score"),
            "non_gating": logos.get("non_gating"),
            "note": "logos conf ~0.2 in fusion stub; equal-weight vote is [NON_GATING] stress test",
        },
        "arms": arms,
        "evaluation": _evaluate_arms(arms),
    }


def build_report(
    *,
    kospi: dict[str, Any],
    btc: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": "multilens_equal_weight_sandbox_3arm_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "sandbox_id": "v2_equal_weight_sandbox_3arm",
        "design": {
            "arm_a": "instrument-specific baseline (current SSOT best weights)",
            "arm_b": "myeongni+sasang+logos equal 1/3; science 0",
            "arm_c": "50% cultural equal + 50% science proxy (macro/momentum/ensemble)",
            "four_ai_mode": "current",
            "logos_role": "NON_GATING — direction vote only in blend weights",
        },
        "legs": {"kospi": kospi, "btc": btc},
        "operator_lines": [
            "- [MKM-SANDBOX-3ARM] research_only; B-track only.",
            "- [MKM-SANDBOX-3ARM] arm_c tests commander equal Logos + science 50/50 hypothesis.",
            "- [MKM-SANDBOX-3ARM] Track A compression 47.5% and live ensemble unchanged.",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2025-11-01")
    ap.add_argument("--date-to", default="2026-06-05")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rules = _read_json(EVOLUTION_RULES)
    if not rules:
        print("Missing evolution rules", file=sys.stderr)
        return 2

    kospi = run_instrument(
        instrument="kospi",
        panel_csv=KOSPI_PANEL,
        ohlcv_csv=KOSPI_CSV,
        date_from=args.date_from,
        date_to=min(args.date_to, "2026-05-30"),
        rules=rules,
    )
    btc = run_instrument(
        instrument="btc",
        panel_csv=BTC_PANEL,
        ohlcv_csv=BTC_CSV,
        date_from=args.date_from,
        date_to=args.date_to,
        rules=rules,
    )
    doc = build_report(kospi=kospi, btc=btc)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    for leg in ("kospi", "btc"):
        ev = doc["legs"][leg]["evaluation"]
        print(
            f"  {leg}: arm_c_delta={ev.get('delta_directional_arm_c_minus_a')} "
            f"promotion_candidate={ev.get('research_promotion_candidate')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
