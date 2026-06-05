#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""KOSPI lens-combo ablation backtest [HYPO][research_only].

Fixed arms for WATCH_ABLATION_RUN:
  - lens3_runtime        (v2_lens3_heavy: session + 명리 + 사상 + macro, no 4AI)
  - sasang_myeongni_only   (사상 + 명리 independent channels only)
  - three_lens_runtime     (명리 + 사상 + Logos [NON_GATING], strict 3-lens)
  - lens3_4ai_overlay      (lens3_runtime + Absolute Balance 4AI coordinator)

Reuses causal scoring from run_kospi_multilens_blend_backtest_v1.
"""

from __future__ import annotations

import argparse
import json
import sys
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.kospi_june2026_multilens_blend_v1 import default_weights_v2  # noqa: E402
from scripts.run_kospi_multilens_blend_backtest_v1 import (  # noqa: E402
    EVOLUTION_RULES,
    KOSPI_CSV,
    _load_closes,
    _load_panel,
    _normalize_weights,
    _predict_v2,
    _read_json,
    _score_series,
    _variant_catalog,
)
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    load_ensemble_kospi_per_date,
    load_static_lenses,
)

DEFAULT_PANEL_FULL = ROOT / "reports/btrack_session_myeongni_panel_full_window_v1.csv"
DEFAULT_PANEL_252 = ROOT / "reports/btrack_session_myeongni_panel_252d_v1.csv"
DEFAULT_OUT = ROOT / "reports/kospi_lens_ablation_backtest_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ablation_arm_catalog(rules: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Named ablation arms — subset of multilens sweep with explicit labels."""
    v2_keys = list(default_weights_v2().keys())
    base_catalog = _variant_catalog(rules)
    lens3 = deepcopy(base_catalog["v2_lens3_heavy"])

    zeroed = {k: 0.0 for k in v2_keys}
    sasang_myeongni = deepcopy(zeroed)
    sasang_myeongni.update({"myeongni_independent": 0.478, "sasang": 0.522})

    three_lens = deepcopy(zeroed)
    three_lens.update(
        {
            "myeongni_independent": 0.34,
            "sasang": 0.33,
            "logos_non_gating": 0.33,
        }
    )

    return {
        "lens3_runtime": {
            "arm_label": "3AI_runtime_session_macro",
            "arm_label_ko": "session+명리+사상+macro (활성 v2_lens3_heavy)",
            "profile": "v2_multilens",
            "four_ai_mode": "none",
            "weights": lens3["weights"],
            "note": lens3.get("note"),
            "maps_to_variant_id": "v2_lens3_heavy",
        },
        "sasang_myeongni_only": {
            "arm_label": "sasang_myeongni_only",
            "arm_label_ko": "사상+명리 단독 (session/macro/logos/field/mom/ensemble=0)",
            "profile": "v2_multilens",
            "four_ai_mode": "none",
            "weights": _normalize_weights(sasang_myeongni, v2_keys),
            "note": "independent myeongni+sasang channels only",
            "maps_to_variant_id": None,
        },
        "three_lens_runtime": {
            "arm_label": "three_lens_logos_runtime",
            "arm_label_ko": "명리+사상+성경(Logos) 3렌즈 [NON_GATING]",
            "profile": "v2_multilens",
            "four_ai_mode": "none",
            "weights": _normalize_weights(three_lens, v2_keys),
            "note": "strict 3-lens stack without session/macro",
            "maps_to_variant_id": None,
        },
        "lens3_4ai_overlay": {
            "arm_label": "lens3_4ai_absolute_balance",
            "arm_label_ko": "lens3_runtime + 4AI Absolute Balance overlay",
            "profile": "v2_multilens",
            "four_ai_mode": "current",
            "weights": lens3["weights"],
            "note": "same weights as lens3_runtime with 4AI coordinator",
            "maps_to_variant_id": "v2_lens3_heavy_4ai_current",
        },
    }


def _rank_key(metrics: dict[str, Any]) -> tuple[float, float, int]:
    soft = metrics.get("soft_hit_rate")
    direc = metrics.get("directional_hit_rate")
    return (
        float(soft) if soft is not None else -1.0,
        float(direc) if direc is not None else -1.0,
        int(metrics.get("n_scored") or 0),
    )


def _delta_pp(base: float | None, other: float | None) -> float | None:
    if base is None or other is None:
        return None
    return round((other - base) * 100.0, 2)


def run_ablation(
    *,
    panel_by_date: dict[str, dict[str, str]],
    closes: dict[str, float],
    date_from: str,
    date_to: str,
    rules: dict[str, Any],
    neutral_bps: float = 5.0,
) -> dict[str, Any]:
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = dict(rules.get("blend_policy_v2") or {})
    coord_policy = dict(rules.get("four_ai_coordinator_policy") or {})
    static_lenses = load_static_lenses()

    eval_dates = sorted(d for d in panel_by_date if date_from <= d <= date_to)
    eval_dates = [d for d in eval_dates if d in closes]
    ensemble_by_date = load_ensemble_kospi_per_date(eval_dates)

    arms = ablation_arm_catalog(rules)
    rows: list[dict[str, Any]] = []

    for arm_id, spec in arms.items():
        weights = spec["weights"]
        four_ai_mode = str(spec["four_ai_mode"])
        preds: dict[str, str] = {}
        diverge_from_v2 = 0
        v2_preds: dict[str, str] = {}

        for dk in eval_dates:
            pred, meta = _predict_v2(
                dk,
                panel_row=panel_by_date[dk],
                closes=closes,
                static_lenses=static_lenses,
                ensemble_row=ensemble_by_date.get(dk),
                weights=weights,
                blend_policy=blend_policy,
                neutral_band=neutral_band,
                four_ai_mode=four_ai_mode,
                coord_policy=coord_policy,
            )
            preds[dk] = pred
            v2_dir = str(meta.get("v2") or pred)
            v2_preds[dk] = v2_dir
            if four_ai_mode != "none" and v2_dir != pred:
                diverge_from_v2 += 1

        metrics = _score_series(preds, closes=closes, neutral_bps=neutral_bps)
        pred_neutral_rate = round(
            sum(1 for p in preds.values() if p == "neutral") / len(preds), 4
        ) if preds else None

        rows.append(
            {
                "arm_id": arm_id,
                "arm_label": spec["arm_label"],
                "arm_label_ko": spec["arm_label_ko"],
                "four_ai_mode": four_ai_mode,
                "weights": weights,
                "note": spec.get("note"),
                "maps_to_variant_id": spec.get("maps_to_variant_id"),
                "diverge_from_v2_days": diverge_from_v2 if four_ai_mode != "none" else 0,
                "pred_neutral_rate": pred_neutral_rate,
                "metrics": metrics,
            }
        )

    ranked = sorted(rows, key=lambda r: _rank_key(r.get("metrics") or {}), reverse=True)
    best = ranked[0] if ranked else None

    by_id = {r["arm_id"]: r for r in rows}
    lens3 = by_id.get("lens3_runtime", {}).get("metrics") or {}
    lens3_soft = lens3.get("soft_hit_rate")
    lens3_4ai = by_id.get("lens3_4ai_overlay", {}).get("metrics") or {}
    lens3_4ai_soft = lens3_4ai.get("soft_hit_rate")

    comparisons: list[dict[str, Any]] = []
    for r in rows:
        m = r.get("metrics") or {}
        comparisons.append(
            {
                "arm_id": r["arm_id"],
                "soft_hit_rate": m.get("soft_hit_rate"),
                "delta_soft_pp_vs_lens3_runtime": _delta_pp(lens3_soft, m.get("soft_hit_rate")),
                "delta_soft_pp_vs_lens3_4ai_overlay": _delta_pp(lens3_4ai_soft, m.get("soft_hit_rate")),
            }
        )

    overlay_uplift_pp = _delta_pp(lens3_soft, lens3_4ai_soft)
    warnings = _methodology_warnings(rows)

    return {
        "schema": "kospi_lens_ablation_backtest_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "track_wall": "no_track_a_live_auto_merge",
        "watch_ablation_run": True,
        "window": {
            "date_from": date_from,
            "date_to": date_to,
            "n_calendar_days": len(eval_dates),
        },
        "neutral_bps": neutral_bps,
        "static_lens_note": "Independent lenses use latest artifact snapshot (not walk-forward refreshed).",
        "best_arm": best,
        "ranked_arms": ranked,
        "four_ai_overlay_uplift_pp_vs_lens3_runtime": overlay_uplift_pp,
        "comparisons": comparisons,
        "methodology_warnings": warnings,
        "verdict_ko": _verdict_ko(ranked, overlay_uplift_pp, warnings),
        "arms": rows,
    }


def _methodology_warnings(rows: list[dict[str, Any]]) -> list[str]:
    """Flag arms that lean on static lens snapshots (not per-date walk-forward)."""
    out: list[str] = []
    for r in rows:
        aid = str(r.get("arm_id") or "")
        w = r.get("weights") or {}
        session_w = float(w.get("session_myeongni") or 0.0)
        mom_w = float(w.get("momentum_overlay") or 0.0)
        if session_w <= 0.0 and mom_w <= 0.0:
            rate = r.get("pred_neutral_rate")
            out.append(
                f"{aid}: session/momentum=0 — independent lenses are latest-artifact snapshots "
                f"(not walk-forward); pred_neutral_rate={rate}. Headline soft HR may reflect "
                "fixed-direction bias, not causal forecast skill."
            )
    out.append(
        "All arms: macro/logos/sasang/myeongni static paths share one JSON snapshot per run "
        "(same caveat as kospi_multilens_blend_backtest_v1)."
    )
    return out


def _verdict_ko(
    ranked: list[dict[str, Any]],
    overlay_uplift_pp: float | None,
    warnings: list[str],
) -> str:
    if not ranked:
        return "표본 없음 — panel/OHLCV 확인 필요."
    best = ranked[0]
    bid = best.get("arm_id")
    soft = (best.get("metrics") or {}).get("soft_hit_rate")
    soft_pct = f"{float(soft) * 100:.2f}%" if soft is not None else "n/a"
    uplift = f"{overlay_uplift_pp:+.2f}pp" if overlay_uplift_pp is not None else "n/a"
    return (
        f"최고 soft HR={soft_pct} ({bid}). "
        f"4AI overlay vs lens3_runtime 델타={uplift}. "
        "apply·Track A·실매매 합선 금지."
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL_FULL)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--date-from", default="1996-12-11")
    ap.add_argument("--date-to", default="2026-06-05")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--also-window",
        action="append",
        default=[],
        metavar="FROM:TO:TAG",
        help="Extra window e.g. 2025-11-01:2026-05-30:recent140d",
    )
    args = ap.parse_args(argv)

    if not args.panel_csv.is_file():
        print(f"Missing panel: {args.panel_csv}", file=sys.stderr)
        return 2
    if not args.kospi_csv.is_file():
        print(f"Missing kospi csv: {args.kospi_csv}", file=sys.stderr)
        return 2

    rules = _read_json(EVOLUTION_RULES)
    panel = _load_panel(args.panel_csv)
    closes = _load_closes(args.kospi_csv)
    neutral_bps = float(rules.get("neutral_bps", 5.0))

    primary = run_ablation(
        panel_by_date=panel,
        closes=closes,
        date_from=args.date_from,
        date_to=args.date_to,
        rules=rules,
        neutral_bps=neutral_bps,
    )

    extra_windows: list[dict[str, Any]] = []
    for spec in args.also_window:
        parts = spec.split(":")
        if len(parts) != 3:
            print(f"Bad --also-window (need FROM:TO:TAG): {spec}", file=sys.stderr)
            return 2
        w_from, w_to, tag = parts
        wdoc = run_ablation(
            panel_by_date=panel,
            closes=closes,
            date_from=w_from,
            date_to=w_to,
            rules=rules,
            neutral_bps=neutral_bps,
        )
        wdoc["window_tag"] = tag
        extra_windows.append(wdoc)

    doc = {
        **primary,
        "primary_window_tag": "main",
        "extra_windows": extra_windows,
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_lens_ablation_backtest_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    best = doc.get("best_arm") or {}
    m = best.get("metrics") or {}
    print(
        f"WROTE: {args.output.resolve()} window={args.date_from}..{args.date_to} "
        f"n={doc['window']['n_calendar_days']} best={best.get('arm_id')} "
        f"soft={m.get('soft_hit_rate')} overlay_uplift_pp={doc.get('four_ai_overlay_uplift_pp_vs_lens3_runtime')}"
    )
    for ew in extra_windows:
        b = ew.get("best_arm") or {}
        bm = b.get("metrics") or {}
        print(
            f"  extra [{ew.get('window_tag')}] n={ew['window']['n_calendar_days']} "
            f"best={b.get('arm_id')} soft={bm.get('soft_hit_rate')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
