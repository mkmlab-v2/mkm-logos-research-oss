#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Sasang veto blend shadow: baseline vs sasang→neutral when force_hold [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_june2026_channel_input_audit_v1 import _momentum_from_row  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_june2026_multilens_blend_v1 import blend_v2_multilens, load_ensemble_kospi_per_date, load_static_lenses  # noqa: E402
from scripts.kospi_lens_per_date_static_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
    load_lens_jsonl_by_day,
    static_lenses_for_eval_date,
)
from scripts.kospi_sasang_veto_shadow_lib_v1 import (  # noqa: E402
    apply_sasang_veto_to_lenses,
    veto_for_eval_date,
)

DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_sasang_veto_blend_shadow_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _soft_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n_scored": 0, "soft_hit_rate": None, "hits": 0, "fails": 0, "neutral": 0}
    hits = sum(1 for r in rows if r.get("outcome") == "HIT")
    fails = sum(1 for r in rows if r.get("outcome") == "FAIL")
    neut = sum(1 for r in rows if r.get("outcome") == "NEUTRAL_DRAW")
    n = len(rows)
    return {
        "n_scored": n,
        "soft_hit_rate": round((hits + 0.5 * neut) / n, 4),
        "hits": hits,
        "fails": fails,
        "neutral": neut,
    }


def build_shadow(
    *,
    calendar: dict[str, Any],
    eval_doc: dict[str, Any],
    rules: dict[str, Any],
    myeongni_by_day: dict[str, dict[str, Any]],
    sasang_by_day: dict[str, dict[str, Any]],
    as_of_kst: str,
    use_per_date_lenses: bool = True,
) -> dict[str, Any]:
    ym = str(calendar.get("year_month") or "")
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}
    weights = calendar.get("blend_weights_applied") or rules.get("blend_weights_v2") or {}
    baseline_static = load_static_lenses()
    eval_by = {str(r.get("session_date")): r for r in (eval_doc.get("rows") or []) if str(r.get("session_date")) <= as_of_kst}
    ensemble = load_ensemble_kospi_per_date(list(eval_by.keys()))

    baseline_rows: list[dict[str, Any]] = []
    veto_rows: list[dict[str, Any]] = []
    day_detail: list[dict[str, Any]] = []

    for row in calendar.get("rows") or []:
        dk = str(row.get("session_date") or "")
        if dk not in eval_by:
            continue
        ev = eval_by[dk]
        actual = str(ev.get("actual_direction") or "neutral")
        session_map = str(row.get("session_mapping_target") or "sideways")
        session_score = float(row.get("session_direction_score") or 0.0)
        mom_dir = _momentum_from_row(row)

        if use_per_date_lenses:
            lenses = static_lenses_for_eval_date(
                dk, baseline=baseline_static, myeongni_by_day=myeongni_by_day, sasang_by_day=sasang_by_day
            )
        else:
            lenses = baseline_static

        veto = veto_for_eval_date(dk, sasang_by_day)
        pred_base, _, _ = blend_v2_multilens(
            session_map=session_map,
            session_score=session_score,
            momentum_dir=mom_dir,
            static_lenses=lenses,
            ensemble_row=ensemble.get(dk),
            weights=weights,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        lenses_v = apply_sasang_veto_to_lenses(lenses, force_hold=bool(veto.get("force_hold")))
        pred_v, _, _ = blend_v2_multilens(
            session_map=session_map,
            session_score=session_score,
            momentum_dir=mom_dir,
            static_lenses=lenses_v,
            ensemble_row=ensemble.get(dk),
            weights=weights,
            neutral_band=neutral_band,
            blend_policy=blend_policy,
        )
        oc_base = _outcome(pred_base, actual)
        oc_v = _outcome(pred_v, actual)
        baseline_rows.append({"session_date": dk, "outcome": oc_base})
        veto_rows.append({"session_date": dk, "outcome": oc_v})
        rescued = oc_base == "FAIL" and oc_v == "HIT"
        day_detail.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "baseline_direction": pred_base,
                "baseline_outcome": oc_base,
                "veto_direction": pred_v,
                "veto_outcome": oc_v,
                "veto_applied": bool(veto.get("force_hold")),
                "veto_reason_codes": veto.get("reason_codes"),
                "rescued_baseline_fail": rescued,
            }
        )

    base_m = _soft_metrics(baseline_rows)
    veto_m = _soft_metrics(veto_rows)
    delta = None
    if base_m.get("soft_hit_rate") is not None and veto_m.get("soft_hit_rate") is not None:
        delta = round(float(veto_m["soft_hit_rate"]) - float(base_m["soft_hit_rate"]), 4)

    fail_days = [d for d in day_detail if d.get("baseline_outcome") == "FAIL"]
    return {
        "schema": "kospi_sasang_veto_blend_shadow_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "year_month": ym,
        "as_of_kst": as_of_kst,
        "use_per_date_lenses": use_per_date_lenses,
        "baseline": base_m,
        "sasang_veto_blend": veto_m,
        "delta_veto_minus_baseline_soft": delta,
        "n_veto_days": sum(1 for d in day_detail if d.get("veto_applied")),
        "n_rescued_baseline_fail": sum(1 for d in fail_days if d.get("rescued_baseline_fail")),
        "fail_day_detail": [d for d in day_detail if d.get("baseline_outcome") == "FAIL"],
        "days": day_detail,
        "reproduce": "py scripts/build_kospi_sasang_veto_blend_shadow_v1.py --year-month 2026-06",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--as-of-kst", default="2026-06-26")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--eval-json", type=Path, default=None)
    ap.add_argument("--static-lenses-only", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()
    tag = ns.year_month.replace("-", "")
    cal_path = ns.calendar_json or ROOT / f"reports/kospi_{tag}_daily_prophecy_calendar_v1.json"
    if ns.year_month == "2026-06" and not cal_path.is_file():
        cal_path = ROOT / "reports/kospi_june2026_daily_prophecy_calendar_v1.json"
    eval_path = ns.eval_json or ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    if ns.year_month == "2026-06":
        eval_path = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"

    my_by, sa_by, _ = load_lens_jsonl_by_day(DEFAULT_MYEONGNI_JSONL, DEFAULT_SASANG_JSONL)
    doc = build_shadow(
        calendar=_read(cal_path),
        eval_doc=_read(eval_path),
        rules=_read(DEFAULT_RULES),
        myeongni_by_day=my_by,
        sasang_by_day=sa_by,
        as_of_kst=ns.as_of_kst,
        use_per_date_lenses=not ns.static_lenses_only,
    )
    if ns.year_month != "2026-06":
        ns.output = ROOT / f"reports/kospi_{tag}_sasang_veto_blend_shadow_v1_latest.json"
    ns.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_sasang_veto_blend_shadow_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "baseline_soft": doc["baseline"].get("soft_hit_rate"),
                "veto_soft": doc["sasang_veto_blend"].get("soft_hit_rate"),
                "delta": doc.get("delta_veto_minus_baseline_soft"),
                "n_veto_days": doc.get("n_veto_days"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
