#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""June KOSPI macro daily refresh PoC [HYPO][research_only].

Replays published calendar with per-date macro gate (OHLCV research JSONL causal-as-of)
vs global macro_independent_lens snapshot. Myeongni/sasang/field/logos stay on active
baseline — macro channel isolation only. No calendar apply.
"""

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

from scripts.backfill_macro_risk_forward_log_from_ohlcv_v1 import (  # noqa: E402
    build_backfill_rows,
)
from scripts.build_kospi_june2026_channel_input_audit_v1 import (  # noqa: E402
    _momentum_from_row,
    _read_json,
    _rel,
    _resolve_calendar_path,
    _soft_from_outcomes,
)
from scripts.eval_kospi_june2026_daily_prophecy_v1 import _outcome  # noqa: E402
from scripts.kospi_june2026_multilens_blend_v1 import (  # noqa: E402
    blend_v2_multilens,
    load_ensemble_kospi_per_date,
    load_static_lenses,
)
from scripts.kospi_lens_per_date_static_v1 import (  # noqa: E402
    DEFAULT_MACRO_BACKFILL_JSONL,
    load_macro_gate_by_day,
    static_lenses_for_eval_date,
)

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_macro_daily_refresh_poc_latest.json"
DEFAULT_COUNTER_CAL = ROOT / "reports/kospi_202606_macro_daily_refresh_calendar_v1.json"
DEFAULT_MACRO_JSONL = DEFAULT_MACRO_BACKFILL_JSONL
DEFAULT_OPERATIONAL_JSONL = ROOT / "reports/macro_risk/forward/macro_risk_forward_log_v1.jsonl"
DEFAULT_KOSPI_CSV = ROOT / "research/market_data/kospi_daily_external_yf.csv"
ART_MACRO = ROOT / "docs/final/artifacts/macro_independent_lens_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _month_end(year_month: str) -> str:
    ym = year_month.strip()
    if len(ym) != 7 or ym[4] != "-":
        return f"{ym}-30"
    y, m = int(ym[:4]), int(ym[5:7])
    if m in (1, 3, 5, 7, 8, 10, 12):
        last = 31
    elif m in (4, 6, 9, 11):
        last = 30
    else:
        last = 29 if (y % 4 == 0 and (y % 100 != 0 or y % 400 == 0)) else 28
    return f"{y:04d}-{m:02d}-{last:02d}"


def ensure_macro_backfill_jsonl(
    *,
    macro_jsonl: Path,
    csv_path: Path,
    date_from: str,
    date_to: str,
    refresh: bool,
) -> dict[str, Any]:
    """Write or refresh research macro gate JSONL for [date_from, date_to]."""
    need_write = refresh or not macro_jsonl.is_file()
    if not need_write and macro_jsonl.is_file():
        return {"refreshed": False, "path": _rel(macro_jsonl), "reason": "existing_file"}

    rows = build_backfill_rows(
        csv_path=csv_path,
        date_from=date_from,
        date_to=date_to,
        neutral_bps=5.0,
        vol_stress_pct=75.0,
    )
    macro_jsonl.parent.mkdir(parents=True, exist_ok=True)
    with macro_jsonl.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    return {
        "refreshed": True,
        "path": _rel(macro_jsonl),
        "n_rows": len(rows),
        "date_from": date_from,
        "date_to": date_to,
    }


def _global_macro_freshness() -> dict[str, Any]:
    doc = _read_json(ART_MACRO)
    prov = doc.get("provenance") if isinstance(doc.get("provenance"), dict) else {}
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    try:
        ds = float(scores.get("direction_score") or 0.0)
    except (TypeError, ValueError):
        ds = 0.0
    from scripts.kospi_june2026_multilens_blend_v1 import _dir_from_score  # noqa: WPS433

    return {
        "artifact_ts_utc": doc.get("ts_utc"),
        "direction_score": scores.get("direction_score"),
        "direction": _dir_from_score(ds),
        "adapter": (doc.get("macro_stream_outputs") or {}).get("adapter"),
        "source_row_ts_utc": prov.get("row_ts_utc") or doc.get("row_ts_utc"),
        "path": _rel(ART_MACRO),
    }


def _replay_macro_refresh_row(
    row: dict[str, Any],
    *,
    static_lenses: dict[str, Any],
    ensemble_by_date: dict[str, dict[str, Any]],
    weights: dict[str, float],
    neutral_band: float,
    blend_policy: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    dk = str(row.get("session_date"))
    pred, score, detail = blend_v2_multilens(
        session_map=str(row.get("session_mapping_target") or "sideways"),
        session_score=float(row.get("session_direction_score") or 0.0),
        momentum_dir=_momentum_from_row(row),
        static_lenses=static_lenses,
        ensemble_row=ensemble_by_date.get(dk),
        weights=weights,
        neutral_band=neutral_band,
        blend_policy=blend_policy,
    )
    return pred, {"blended_score": score, **detail}


def build_macro_daily_refresh_poc(
    *,
    calendar: dict[str, Any],
    rules: dict[str, Any],
    eval_doc: dict[str, Any] | None,
    macro_gate_by_day: dict[str, dict[str, Any]],
    calendar_path: Path,
    macro_jsonl_meta: dict[str, Any],
    global_macro: dict[str, Any],
    write_counter_calendar: bool,
    counter_calendar_path: Path,
) -> dict[str, Any]:
    rows = calendar.get("rows") if isinstance(calendar.get("rows"), list) else []
    trading_days = [str(r.get("session_date")) for r in rows if r.get("session_date")]
    weights = calendar.get("blend_weights_applied") if isinstance(calendar.get("blend_weights_applied"), dict) else {}
    neutral_band = float(rules.get("neutral_band", 0.06))
    blend_policy = rules.get("blend_policy_v2") if isinstance(rules.get("blend_policy_v2"), dict) else {}

    static_global = load_static_lenses()
    ensemble_by_date = load_ensemble_kospi_per_date(trading_days)
    gate_ok = bool(macro_gate_by_day)

    diffs: list[dict[str, Any]] = []
    counter_rows: list[dict[str, Any]] = []
    active_counts: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    counter_counts: dict[str, int] = {"bull": 0, "bear": 0, "neutral": 0}
    macro_per_date_samples: list[dict[str, Any]] = []

    for row in rows:
        dk = str(row.get("session_date"))
        active_dir = str(row.get("predicted_direction") or "neutral")
        active_counts[active_dir] = active_counts.get(active_dir, 0) + 1

        if not gate_ok:
            counter_dir = active_dir
            blend_detail: dict[str, Any] = {}
            per_static = static_global
            note = "macro_gate_missing_fallback_active"
        else:
            per_static = static_lenses_for_eval_date(
                dk,
                sasang_by_day={},
                myeongni_by_day={},
                baseline=static_global,
                macro_gate_by_day=macro_gate_by_day,
            )
            counter_dir, blend_detail = _replay_macro_refresh_row(
                row,
                static_lenses=per_static,
                ensemble_by_date=ensemble_by_date,
                weights=weights,
                neutral_band=neutral_band,
                blend_policy=blend_policy,
            )
            note = "per_date_macro_gate_replay"
            macro_ch = per_static.get("macro") if isinstance(per_static.get("macro"), dict) else {}
            if macro_ch.get("per_date"):
                macro_per_date_samples.append(
                    {
                        "session_date": dk,
                        "global_macro_direction": static_global.get("macro", {}).get("direction"),
                        "per_date_macro_direction": macro_ch.get("direction"),
                        "decision_state": macro_ch.get("decision_state"),
                        "matched_session_date": macro_ch.get("matched_session_date"),
                        "source": macro_ch.get("source"),
                    }
                )

        counter_counts[counter_dir] = counter_counts.get(counter_dir, 0) + 1
        if counter_dir != active_dir:
            diffs.append(
                {
                    "session_date": dk,
                    "active_direction": active_dir,
                    "counterfactual_direction": counter_dir,
                    "global_macro_direction": static_global.get("macro", {}).get("direction"),
                    "per_date_macro": (per_static.get("macro") if gate_ok else {}),
                    "counter_votes": blend_detail.get("votes"),
                    "counter_resolution": blend_detail.get("winner_resolution"),
                }
            )

        counter_rows.append(
            {
                **row,
                "predicted_direction": counter_dir,
                "predicted_direction_ko": {"bull": "상승", "bear": "하락", "neutral": "횡보·관측"}.get(
                    counter_dir, counter_dir
                ),
                "counterfactual_meta": {
                    "source": note,
                    "active_direction": active_dir,
                    "changed_vs_active": counter_dir != active_dir,
                    "kind": "macro_daily_refresh_poc",
                },
                "blend": blend_detail if gate_ok else row.get("blend"),
            }
        )

    june_days = [d for d in trading_days if d.startswith(calendar.get("year_month", "2026-06")[:7])]
    from scripts.run_three_lens_horizon_empirical_eval_v2 import _gate_asof  # noqa: WPS433

    asof_hits = sum(1 for d in june_days if _gate_asof(macro_gate_by_day, d))

    scored_eval: list[dict[str, Any]] = []
    active_outcomes: list[str] = []
    counter_outcomes: list[str] = []
    for er in (eval_doc or {}).get("rows") or []:
        dk = str(er.get("session_date"))
        actual = str(er.get("actual_direction") or "neutral")
        active_dir = str(er.get("predicted_direction") or "neutral")
        active_oc = str(er.get("outcome") or _outcome(active_dir, actual))
        active_outcomes.append(active_oc)

        counter_row = next((r for r in counter_rows if str(r.get("session_date")) == dk), None)
        counter_dir = str((counter_row or {}).get("predicted_direction") or active_dir)
        counter_oc = _outcome(counter_dir, actual)
        counter_outcomes.append(counter_oc)
        scored_eval.append(
            {
                "session_date": dk,
                "actual_direction": actual,
                "active_direction": active_dir,
                "active_outcome": active_oc,
                "counterfactual_direction": counter_dir,
                "counterfactual_outcome": counter_oc,
            }
        )

    counter_calendar_doc: dict[str, Any] | None = None
    if write_counter_calendar and gate_ok:
        counter_calendar_doc = {
            **{k: v for k, v in calendar.items() if k != "rows"},
            "schema": "kospi_monthly_daily_prophecy_calendar_v2_counterfactual",
            "generated_at_utc": _utc_now(),
            "hypothesis_tier": "B",
            "research_only": True,
            "auto_apply": False,
            "counterfactual_kind": "per_date_macro_gate_ohlcv_research",
            "active_calendar_path": _rel(calendar_path),
            "note_ko": "macro 일별 갱신 PoC — active calendar·evolution apply 금지",
            "rows": counter_rows,
        }
        counter_calendar_path.parent.mkdir(parents=True, exist_ok=True)
        counter_calendar_path.write_text(
            json.dumps(counter_calendar_doc, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    findings: list[str] = []
    if not gate_ok:
        findings.append("macro gate JSONL 없음 — PoC skip")
    else:
        g_dir = static_global.get("macro", {}).get("direction")
        findings.append(
            f"global macro snapshot direction={g_dir} ts={global_macro.get('artifact_ts_utc', '—')}"
        )
        findings.append(
            f"June gate as-of coverage {asof_hits}/{len(june_days)} — "
            f"방향 diff {len(diffs)}/{len(rows)}"
        )
        if scored_eval:
            a_soft = _soft_from_outcomes(active_outcomes)
            c_soft = _soft_from_outcomes(counter_outcomes)
            findings.append(
                f"scored soft {a_soft} → {c_soft} (n={len(scored_eval)}) — macro-only replay, apply 금지"
            )

    return {
        "schema": "kospi_june2026_macro_daily_refresh_poc_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "year_month": calendar.get("year_month") or "2026-06",
        "active_calendar_path": _rel(calendar_path),
        "counter_calendar_path": _rel(counter_calendar_path) if counter_calendar_doc else None,
        "global_macro_snapshot": global_macro,
        "macro_jsonl": macro_jsonl_meta,
        "macro_gate": {
            "n_gate_days_total": len(macro_gate_by_day),
            "june_trading_days": len(june_days),
            "june_asof_coverage": asof_hits,
            "gate_coverage_ratio": round(asof_hits / len(june_days), 4) if june_days else None,
        },
        "macro_per_date_samples": macro_per_date_samples[:21],
        "direction_diffs": diffs,
        "summary": {
            "n_trading_days": len(rows),
            "n_direction_diffs": len(diffs),
            "active_direction_counts": active_counts,
            "counterfactual_direction_counts": counter_counts,
            "scored_forward": {
                "n_scored": len(scored_eval),
                "active_soft_hit_rate": _soft_from_outcomes(active_outcomes),
                "counterfactual_soft_hit_rate": _soft_from_outcomes(counter_outcomes),
                "days": scored_eval,
            },
        },
        "key_findings_ko": findings,
        "recommended_next_ko": (
            "운영 macro_risk_forward_log_v1.jsonl tier-2 병합 PoC; n≥7 scored 후 macro-only soft 재평가. apply 금지."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--calendar-json", type=Path, default=None)
    ap.add_argument("--rules-json", type=Path, default=DEFAULT_RULES)
    ap.add_argument("--eval-json", type=Path, default=DEFAULT_EVAL)
    ap.add_argument("--macro-jsonl", type=Path, default=DEFAULT_MACRO_JSONL)
    ap.add_argument("--operational-jsonl", type=Path, default=DEFAULT_OPERATIONAL_JSONL)
    ap.add_argument("--kospi-csv", type=Path, default=DEFAULT_KOSPI_CSV)
    ap.add_argument("--backfill-from", default="1996-01-01")
    ap.add_argument("--refresh-macro-backfill", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--write-counter-calendar", action="store_true", default=True)
    ap.add_argument("--no-write-counter-calendar", action="store_false", dest="write_counter_calendar")
    ap.add_argument("--counter-calendar-json", type=Path, default=DEFAULT_COUNTER_CAL)
    args = ap.parse_args(argv)

    cal_path = _resolve_calendar_path(args.calendar_json, year_month=args.year_month)
    calendar = _read_json(cal_path)
    if not calendar.get("rows"):
        raise SystemExit(f"Missing calendar rows: {cal_path}")

    date_to = _month_end(args.year_month)
    macro_meta = ensure_macro_backfill_jsonl(
        macro_jsonl=args.macro_jsonl,
        csv_path=args.kospi_csv,
        date_from=args.backfill_from,
        date_to=date_to,
        refresh=args.refresh_macro_backfill,
    )

    macro_gate = load_macro_gate_by_day(
        args.macro_jsonl,
        operational_jsonl=args.operational_jsonl if args.operational_jsonl.is_file() else None,
    )

    doc = build_macro_daily_refresh_poc(
        calendar=calendar,
        rules=_read_json(args.rules_json),
        eval_doc=_read_json(args.eval_json) if args.eval_json.is_file() else None,
        macro_gate_by_day=macro_gate,
        calendar_path=cal_path,
        macro_jsonl_meta=macro_meta,
        global_macro=_global_macro_freshness(),
        write_counter_calendar=args.write_counter_calendar,
        counter_calendar_path=args.counter_calendar_json,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summ = doc["summary"]
    sf = summ.get("scored_forward") or {}
    print(
        f"WROTE: {args.output.resolve()} diffs={summ.get('n_direction_diffs')} "
        f"scored_soft {sf.get('active_soft_hit_rate')}→{sf.get('counterfactual_soft_hit_rate')} "
        f"gate_days={doc.get('macro_gate', {}).get('n_gate_days_total')}"
    )
    if doc.get("counter_calendar_path"):
        print(f"WROTE: {(ROOT / doc['counter_calendar_path']).resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
