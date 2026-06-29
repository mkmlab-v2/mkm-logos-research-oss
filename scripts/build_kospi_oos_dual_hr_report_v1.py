#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Active vs composite shadow dual HR report (raw) [HYPO][research_only]."""

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

DEFAULT_OUT = ROOT / "reports/kospi_oos_dual_hr_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _arm_summary(parallel: dict[str, Any], arm: str) -> dict[str, Any]:
    s = (parallel.get("summary") or {}).get(arm) or {}
    return {
        "soft_hit_rate": s.get("soft_hit_rate"),
        "directional_hit_rate": s.get("directional_hit_rate"),
        "n_scored": s.get("n_scored"),
        "hits": s.get("hits"),
        "fails": s.get("fails"),
        "neutral": s.get("neutral"),
    }


def build_dual_hr_report(
    *,
    year_month: str,
    as_of_kst: str,
    eval_doc: dict[str, Any],
    parallel: dict[str, Any],
    per_date_eval: dict[str, Any] | None = None,
    readiness: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_eval = (eval_doc.get("metrics") or {}) if isinstance(eval_doc.get("metrics"), dict) else {}
    active_arm = _arm_summary(parallel, "active_locked")
    composite_arm = _arm_summary(parallel, "composite_bear_conditional")
    hold_arm = _arm_summary(parallel, "composite_active_hold")

    n_eval = int(eval_doc.get("n_scored") or active_arm.get("n_scored") or 0)
    raw_active = active_eval.get("soft_hit_rate")
    if raw_active is None:
        raw_active = active_arm.get("soft_hit_rate")
    raw_composite = composite_arm.get("soft_hit_rate")
    delta = None
    if raw_active is not None and raw_composite is not None:
        delta = round(float(raw_composite) - float(raw_active), 4)

    per_date_soft = None
    if per_date_eval:
        per_date_soft = (per_date_eval.get("metrics") or {}).get("soft_hit_rate")

    return {
        "schema": "kospi_oos_dual_hr_report_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "production_apply_authorized": False,
        "year_month": year_month,
        "as_of_kst": as_of_kst,
        "n_scored": n_eval,
        "readiness_status": (readiness or {}).get("status"),
        "raw": {
            "active": {
                "arm_id": "active_locked",
                "parse_ok_rate": None,
                "alignment_pass_rate": raw_active,
                "rows": n_eval,
                "source": "published_eval_or_parallel",
            },
            "composite_bear_conditional": {
                "arm_id": "composite_bear_conditional",
                "alignment_pass_rate": raw_composite,
                "rows": composite_arm.get("n_scored"),
                "operational_post_processor": True,
                "note": "shadow arm — not core model quality",
            },
        },
        "repair_v2": {
            "composite_active_hold": {
                "alignment_pass_rate": hold_arm.get("soft_hit_rate"),
                "rows": hold_arm.get("n_scored"),
            },
            "per_date_lens_shadow": {
                "alignment_pass_rate": per_date_soft,
                "rows": per_date_eval.get("n_scored") if per_date_eval else None,
            },
        },
        "delta": {
            "alignment_pass_rate_delta_composite_minus_active": delta,
            "per_date_minus_active": (
                round(float(per_date_soft) - float(raw_active), 4)
                if per_date_soft is not None and raw_active is not None
                else None
            ),
        },
        "parallel_leader": parallel.get("leader_arm"),
        "active_fail_rescues": parallel.get("active_fail_rescues"),
        "headline_ko": (
            f"{year_month} n={n_eval} active soft {raw_active} vs composite {raw_composite} "
            f"(Δ {delta}pp shadow) — apply HOLD"
            if n_eval
            else f"{year_month} n_scored=0 — OOS accumulating, dual HR pending"
        ),
        "reproduce": f"py scripts/build_kospi_oos_dual_hr_report_v1.py --year-month {year_month}",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year-month", default="2026-07")
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ns = ap.parse_args()
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from scripts.kospi_krx_calendar_v1 import last_krx_trading_day_on_or_before
    from datetime import date

    as_of = ns.as_of_kst or last_krx_trading_day_on_or_before(date.today()) or date.today().isoformat()
    tag = ns.year_month.replace("-", "")

    eval_path = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    if ns.year_month == "2026-06":
        eval_path = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
    parallel_path = ROOT / f"reports/kospi_{tag}_parallel_shadow_bundle_v1_latest.json"
    if ns.year_month == "2026-06":
        parallel_path = ROOT / "reports/kospi_june2026_parallel_shadow_bundle_v1_latest.json"
    per_date_eval_path = ROOT / f"reports/kospi_{tag}_per_date_lens_shadow_eval_latest.json"
    if ns.year_month == "2026-06":
        per_date_eval_path = ROOT / "reports/kospi_june2026_per_date_lens_shadow_eval_latest.json"

    doc = build_dual_hr_report(
        year_month=ns.year_month,
        as_of_kst=as_of,
        eval_doc=_read(eval_path),
        parallel=_read(parallel_path),
        per_date_eval=_read(per_date_eval_path) if per_date_eval_path.is_file() else None,
        readiness=_read(ROOT / "reports/kospi_july_forward_oos_readiness_v1_latest.json"),
    )
    out = ns.output
    if ns.year_month != "2026-06":
        out = ROOT / f"reports/kospi_{tag}_oos_dual_hr_report_v1_latest.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_oos_dual_hr_report_v1_latest.json"
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "n_scored": doc["n_scored"], "headline": doc["headline_ko"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
