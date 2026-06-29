#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Build KOSPI OOS significance appendix from prophecy eval [HYPO][research_only]."""

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

from scripts.kospi_oos_significance_lib_v1 import (  # noqa: E402
    metrics_from_eval_rows,
    significance_block,
)
from scripts.kospi_prophecy_lane_routing_v1 import SCORING_LANE_ID  # noqa: E402

DEFAULT_EVAL = ROOT / "reports/kospi_june2026_daily_prophecy_eval_latest.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_oos_significance_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/kospi_june2026_oos_significance_v1_latest.json"
JULY_EVAL = ROOT / "reports/kospi_202607_daily_prophecy_eval_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _paths_for_month(year_month: str) -> tuple[Path, Path]:
    tag = year_month.replace("-", "")
    ev = ROOT / f"reports/kospi_{tag}_daily_prophecy_eval_latest.json"
    if year_month == "2026-06" and not ev.is_file():
        ev = DEFAULT_EVAL
    out = ROOT / f"reports/kospi_{tag}_oos_significance_v1_latest.json"
    return ev, out


def build_significance_report(
    eval_doc: dict[str, Any],
    *,
    model_id: str = "v2_lens3_heavy",
    july_eval: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rows = eval_doc.get("rows") if isinstance(eval_doc.get("rows"), list) else []
    m = metrics_from_eval_rows(rows)
    dir_block = significance_block(
        label="directional_hit_rate",
        successes=float(m["hit"]),
        n=int(m["n_directional_bets"]),
    )
    soft_block = significance_block(
        label="soft_hit_rate",
        successes=float(m["soft_successes"]),
        n=int(m["n_scored"]),
    )

    july_section: dict[str, Any] | None = None
    if july_eval:
        jm = metrics_from_eval_rows(july_eval.get("rows") or [])
        if jm["n_scored"] > 0:
            july_section = {
                "year_month": july_eval.get("year_month"),
                "metrics": jm,
                "directional_significance": significance_block(
                    label="directional_hit_rate",
                    successes=float(jm["hit"]),
                    n=int(jm["n_directional_bets"]),
                ),
                "soft_significance": significance_block(
                    label="soft_hit_rate",
                    successes=float(jm["soft_successes"]),
                    n=int(jm["n_scored"]),
                ),
            }
        else:
            july_section = {
                "year_month": july_eval.get("year_month"),
                "n_scored": 0,
                "status": "awaiting_oos_forward",
                "oos_forward_start": "2026-07-01",
            }

    dir_ci = dir_block["wilson_95_ci"]
    headline = (
        f"directional {m['directional_hit_rate']} (n_bets={m['n_directional_bets']}) "
        f"Wilson95 [{dir_ci[0]}, {dir_ci[1]}] — H0:p=0.5 "
        f"{'기각 실패' if dir_block['null_inside_wilson_ci'] else '기각 가능'}"
    )

    return {
        "schema": "kospi_oos_significance_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "auto_apply": False,
        "prophecy_lane": SCORING_LANE_ID,
        "prophecy_lane_role": "scoring_shadow",
        "model_id": model_id,
        "eval_source": eval_doc.get("calendar_path"),
        "as_of_kst": eval_doc.get("as_of_kst"),
        "year_month": eval_doc.get("year_month"),
        "raw_metrics": m,
        "significance": {
            "directional": dir_block,
            "soft": soft_block,
        },
        "july_oos_forward": july_section,
        "research_pointers": {
            "cpcv_literature": "docs/research/BTRACK_MAX_PROPHECY_EVOLUTION_LIT_REVIEW_2026-06-26.md",
            "lane_routing": "docs/final/artifacts/kospi_prophecy_lane_routing_v1_latest.json",
            "briefing_primary": "reports/mkm_parallel_advisory_brief_v1_latest.json",
            "cpcv_note_ko": "백테스트 승격 주장 전 CPCV+purging PoC 권장 — 본 부록은 포워드 binomial만.",
        },
        "headline_ko": headline,
        "verdict_ko": (
            f"6월 포워드: directional·soft 모두 Wilson 95% CI가 p=0.5 포함 — "
            f"통계적 엣지 입증 불가. {m['fail_pattern_ko']}. "
            "브리핑 본선(parallel_advisory)과 혼동 금지."
        ),
        "reproduce": "py scripts/build_kospi_june2026_oos_significance_v1.py --year-month 2026-06",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--eval", type=Path, default=None)
    ap.add_argument("--year-month", default="2026-06")
    ap.add_argument("--model-id", default="v2_lens3_heavy")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact", type=Path, default=DEFAULT_ART)
    ap.add_argument("--include-july", action="store_true", default=True)
    args = ap.parse_args()

    ev_p, month_out = _paths_for_month(args.year_month)
    ev_p = args.eval or ev_p
    if not ev_p.is_absolute():
        ev_p = ROOT / ev_p
    out_p = args.output if args.output.is_absolute() else ROOT / args.output
    if args.output == DEFAULT_OUT and args.year_month != "2026-06":
        out_p = month_out

    eval_doc = _read(ev_p)
    if not eval_doc:
        print(json.dumps({"ok": False, "error": f"missing eval: {ev_p}"}, ensure_ascii=False))
        return 1

    july_doc = _read(JULY_EVAL) if args.include_july else None
    doc = build_significance_report(eval_doc, model_id=args.model_id, july_eval=july_doc)

    art_p = args.artifact if args.artifact.is_absolute() else ROOT / args.artifact
    for p in (out_p, art_p, DEFAULT_OUT if args.year_month == "2026-06" else out_p):
        if p == DEFAULT_OUT and out_p != DEFAULT_OUT and args.year_month != "2026-06":
            continue
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "out": str(out_p),
                "headline_ko": doc.get("headline_ko"),
                "directional_wilson": doc["significance"]["directional"]["wilson_95_ci"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
