#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Proxy forward eval (prior month, same blend) when June elapsed days are scarce [HYPO]."""

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

from scripts.build_kospi_june2026_daily_prophecy_calendar_v1 import build_calendar  # noqa: E402
from scripts.eval_kospi_june2026_daily_prophecy_v1 import eval_calendar  # noqa: E402

EVOLUTION_RULES = ROOT / "data/commander/kospi_june2026_prophecy_evolution_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_proxy_forward_eval_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _month_end_as_of(proxy_year_month: str) -> str:
    y, m = proxy_year_month.split("-")
    yi, mi = int(y), int(m)
    if mi == 12:
        return f"{yi:04d}-12-31"
    from datetime import date, timedelta

    end = date(yi, mi + 1, 1) - timedelta(days=1)
    return end.isoformat()


def run_proxy_forward_eval(
    *,
    rules: dict[str, Any],
    proxy_year_month: str,
    candidate_id: str,
    as_of_kst: str | None = None,
) -> dict[str, Any]:
    as_of = as_of_kst or _month_end_as_of(proxy_year_month)
    active_cal = build_calendar(
        year_month=proxy_year_month,
        skip_panel=True,
        profile="v2_multilens",
    )
    candidate_cal = build_calendar(
        year_month=proxy_year_month,
        skip_panel=True,
        profile="v2_multilens",
        weights_candidate_id=candidate_id,
    )
    active_eval = eval_calendar(active_cal, as_of_kst=as_of)
    candidate_eval = eval_calendar(candidate_cal, as_of_kst=as_of)
    policy = rules.get("proxy_forward_policy") if isinstance(rules.get("proxy_forward_policy"), dict) else {}
    min_required = int(policy.get("min_scored_for_promotion_substitute", 15))
    active_n = int(active_eval.get("n_scored") or 0)
    gate_pass = active_n >= min_required
    return {
        "schema": "kospi_june2026_proxy_forward_eval_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "role": "june_forward_substitute_not_live_june",
        "proxy_year_month": proxy_year_month,
        "as_of_kst": as_of,
        "candidate_id": candidate_id,
        "min_required": min_required,
        "gate_pass": gate_pass,
        "active": {
            "n_scored": active_eval.get("n_scored"),
            "metrics": active_eval.get("metrics"),
        },
        "candidate": {
            "n_scored": candidate_eval.get("n_scored"),
            "metrics": candidate_eval.get("metrics"),
        },
        "note_ko": (
            f"{proxy_year_month} 동일 blend 채점 — 6월 경과일 부족 시 apply 검토 보조. "
            "Track A·실매매·June 실경과 대체 아님."
        ),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proxy-year-month", default="2026-05")
    ap.add_argument("--candidate-id", default=None)
    ap.add_argument("--as-of-kst", default=None)
    ap.add_argument("--rules-json", type=Path, default=EVOLUTION_RULES)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    rules = _read_json(args.rules_json)
    policy = rules.get("weight_candidate_policy") if isinstance(rules.get("weight_candidate_policy"), dict) else {}
    cid = args.candidate_id or str(policy.get("active_candidate_id") or "v2_lens3_heavy")
    doc = run_proxy_forward_eval(
        rules=rules,
        proxy_year_month=str(args.proxy_year_month),
        candidate_id=cid,
        as_of_kst=args.as_of_kst,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        f"WROTE: {args.output.resolve()} proxy={args.proxy_year_month} "
        f"n_scored={doc['active']['n_scored']}/{doc['min_required']} gate={doc['gate_pass']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
