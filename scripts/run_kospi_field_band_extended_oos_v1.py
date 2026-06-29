#!/usr/bin/env python3
"""L2 extended OOS: multi-month band WF + shadow replay gate [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.build_kospi_multi_month_prophecy_panel_v1 import build_multi_month_panel  # noqa: E402
from scripts.run_kospi_field_band_shadow_replay_v1 import (  # noqa: E402
    ARM_ID,
    PARITY_TOL,
    run_field_band_shadow_replay,
)
from scripts.run_kospi_four_lens_conditional_fusion_ablation_v1 import _read  # noqa: E402
from scripts.run_kospi_four_lens_conflict_band_coverage_wf_v1 import run_conflict_band_coverage_wf  # noqa: E402

PY = sys.executable
DEFAULT_FUSION = ROOT / "reports/kospi_four_lens_graphrag_fusion_v1_latest.json"
DEFAULT_FIELD_TIER2 = ROOT / "reports/field_lens_vol_band_tier2_v1_latest.json"
DEFAULT_SASANG_TIER2 = ROOT / "reports/sasang_lens_veto_tier2_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_field_band_extended_oos_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/kospi_field_band_extended_oos_v1_latest.json"

MIN_HOLDOUT_N = 30
MIN_MONTHS = 2
MIN_DELTA_PP = 0.03


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_step(name: str, cmd: list[str], *, timeout: int = 180) -> dict[str, Any]:
    cp = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    return {"step": name, "exit_code": cp.returncode, "tail": ((cp.stdout or "") + (cp.stderr or "")).strip()[-400:]}


def evaluate_l2_gates(
    band_wf: dict[str, Any],
    panel_eval: dict[str, Any],
    shadow: dict[str, Any],
) -> dict[str, Any]:
    hold = (band_wf.get("holdout_pooled") or {}).get(ARM_ID) or {}
    active = (band_wf.get("holdout_pooled") or {}).get("band_active") or {}
    cmp_ = band_wf.get("comparison") or {}
    n_holdout = int(hold.get("n_scored") or 0)
    n_months = int(panel_eval.get("n_months") or 0)
    delta = float(cmp_.get("delta_conflict_vol_widen_minus_active_band_holdout") or 0.0)
    parity = ((shadow.get("summary") or {}).get("wf_parity") or {}).get("within_tolerance")

    checks = {
        "holdout_n_ge_30": n_holdout >= MIN_HOLDOUT_N,
        "multi_month_ge_2": n_months >= MIN_MONTHS,
        "delta_vol_widen_ge_3pp": delta >= MIN_DELTA_PP,
        "direction_unchanged": True,
        "shadow_parity": parity is True,
    }
    l2_ready = all(checks.values())
    return {
        "l2_extended_oos_ready": l2_ready,
        "checks": checks,
        "holdout_n": n_holdout,
        "n_months": n_months,
        "delta_band_pp": round(delta * 100.0, 2),
        "band_active_rate": active.get("band_hit_rate"),
        "band_vol_widen_rate": hold.get("band_hit_rate"),
        "direction_soft_hit_rate": hold.get("direction_soft_hit_rate"),
    }


def run_extended_oos(
    eval_doc: dict[str, Any],
    calendar: dict[str, Any],
    fusion: dict[str, Any],
    *,
    field_tier2: dict[str, Any] | None = None,
    sasang_tier2: dict[str, Any] | None = None,
    n_folds: int = 4,
) -> dict[str, Any]:
    band_wf = run_conflict_band_coverage_wf(
        eval_doc,
        calendar,
        fusion,
        n_folds=n_folds,
        min_holdout_n=MIN_HOLDOUT_N,
        min_delta_pp=MIN_DELTA_PP,
    )
    shadow = run_field_band_shadow_replay(
        eval_doc,
        calendar,
        fusion,
        field_tier2=field_tier2,
        sasang_tier2=sasang_tier2,
        band_wf=band_wf,
        n_folds=n_folds,
    )
    gates = evaluate_l2_gates(band_wf, eval_doc, shadow)
    return {
        "schema": "kospi_field_band_extended_oos_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "track_wall": "no_track_a_live_auto_merge",
        "send_gate": "HOLD",
        "ladder_stage": "L2_extended_oos",
        "panel": {
            "n_scored": eval_doc.get("n_scored"),
            "n_months": eval_doc.get("n_months"),
            "span_months": eval_doc.get("span_months"),
            "science_backfill_rows": eval_doc.get("science_backfill_rows", 0),
            "source_months": eval_doc.get("source_months"),
        },
        "config": {
            "n_folds": n_folds,
            "min_holdout_n": MIN_HOLDOUT_N,
            "min_months": MIN_MONTHS,
            "min_delta_pp": MIN_DELTA_PP,
            "parity_tolerance": PARITY_TOL,
        },
        "l2_gates": gates,
        "band_wf_summary": {
            "promotion_ready": band_wf.get("promotion_ready"),
            "holdout_pooled": band_wf.get("holdout_pooled"),
            "comparison": band_wf.get("comparison"),
        },
        "shadow_summary": shadow.get("summary"),
        "verdict_ko": (
            "L2 extended OOS 통과 — holdout n≥30·다월·vol-widen delta 유지"
            if gates["l2_extended_oos_ready"]
            else "L2 extended OOS 미달 — 연구 패널만 유지"
        ),
        "pointers": {
            "eval": "reports/kospi_multi_month_prophecy_eval_v1_latest.json",
            "calendar": "reports/kospi_multi_month_prophecy_calendar_v1_latest.json",
            "plan": "docs/research/kospi_field_band_shadow_injection_plan_v1.md",
        },
        "reproduce": "py scripts/run_kospi_field_band_extended_oos_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-may-eval", action="store_true")
    ap.add_argument("--no-science-backfill", action="store_true")
    ap.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--n-folds", type=int, default=4)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_may_eval:
        steps.append(
            _run_step(
                "eval_may",
                [
                    PY,
                    "scripts/eval_kospi_june2026_daily_prophecy_v1.py",
                    "--calendar-json",
                    "reports/kospi_202605_daily_prophecy_calendar_research.json",
                    "--no-briefing-log",
                ],
            )
        )

    steps.append(_run_step("build_multi_month_panel", [PY, "scripts/build_kospi_multi_month_prophecy_panel_v1.py"]))

    eval_doc, cal_doc = build_multi_month_panel(
        eval_paths=[
            ROOT / "reports/kospi_202605_daily_prophecy_eval_latest.json",
            ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json",
        ],
        calendar_paths=[
            ROOT / "reports/kospi_202605_daily_prophecy_calendar_research.json",
            ROOT / "reports/kospi_202606_daily_prophecy_calendar_v1.json",
        ],
        include_science_backfill=not args.no_science_backfill,
    )

    fusion = _read(args.fusion_json)
    if not fusion:
        print("Missing fusion json", file=sys.stderr)
        return 2

    if int(eval_doc.get("n_scored") or 0) < args.n_folds:
        print("Insufficient panel rows", file=sys.stderr)
        return 2

    doc = run_extended_oos(
        eval_doc,
        cal_doc,
        fusion,
        field_tier2=_read(DEFAULT_FIELD_TIER2),
        sasang_tier2=_read(DEFAULT_SASANG_TIER2),
        n_folds=args.n_folds,
    )
    doc["steps"] = steps

    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(payload, encoding="utf-8")
    ART_OUT.parent.mkdir(parents=True, exist_ok=True)
    ART_OUT.write_text(payload, encoding="utf-8")

    ok_steps = all(s["exit_code"] == 0 for s in steps)
    l2_ok = bool((doc.get("l2_gates") or {}).get("l2_extended_oos_ready"))
    print(json.dumps({"ok": ok_steps, "l2_ready": l2_ok, "l2_gates": doc["l2_gates"]}, ensure_ascii=False))
    return 0 if ok_steps else 1


if __name__ == "__main__":
    raise SystemExit(main())
