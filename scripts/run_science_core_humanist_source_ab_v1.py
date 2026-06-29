#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare Science Core holdout: calendar stub vs sidecar vs market_sasang per-date [HYPO]."""
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

from scripts.btrack_multilens_per_date_core_v1 import (  # noqa: E402
    DEFAULT_LOGOS_LENS,
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_SASANG_JSONL,
)
from scripts.build_btrack_humanist_jsonl_from_sidecar_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_OUT,
    DEFAULT_SASANG_OUT,
    export_humanist_jsonl_from_sidecar,
    _write_jsonl,
)

DEFAULT_MARKET_SASANG_JSONL = ROOT / "reports/btrack_market_sasang_per_date_v1.jsonl"
DEFAULT_MYEONGNI_PER_DATE_JSONL = ROOT / "reports/btrack_myeongni_per_date_v1.jsonl"
DEFAULT_EXTENDED_SIDECAR = ROOT / "reports/btrack_prophecy_score_insight_sidecar_science_core_panel_v1.json"
from scripts.run_science_core_holdout_combo_v1 import run_holdout_bundle  # noqa: E402
from scripts.run_science_core_horizon_empirical_eval_v1 import (  # noqa: E402
    DEFAULT_SCIENCE_JSONL_KOSPI,
    _ensure_science_jsonl,
)
import scripts.run_three_lens_horizon_empirical_eval_v1 as v1  # noqa: E402

DEFAULT_OUT = ROOT / "reports/science_core_humanist_source_ab_v1_latest.json"
ART_OUT = ROOT / "docs/final/artifacts/science_core_humanist_source_ab_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _summarize_holdout(doc: dict[str, Any], label: str) -> dict[str, Any]:
    attach = (doc.get("kospi") or {}).get("attach_recommendation") or {}
    k_holdout = (doc.get("kospi") or {}).get("horizon_holdout") or {}
    return {
        "label": label,
        "always_attach_recommended": attach.get("always_attach_recommended"),
        "holdout_uplift_soft": (attach.get("holdout_best_combo") or {}).get("uplift_vs_science_alone"),
        "holdout_best_combo": (attach.get("holdout_best_combo") or {}).get("best_lens_id"),
        "science_short_1d_soft": ((k_holdout.get("rate_matrix") or {}).get("science_core") or {}).get(
            "short_1d", {}
        ).get("soft_hit_rate"),
        "n_eval_dates": k_holdout.get("n_eval_dates"),
    }


def run_ab(
    *,
    date_from: str,
    date_to: str,
    train_to: str,
    holdout_from: str,
    holdout_to: str,
    sidecar_path: Path | None,
    market_sasang_jsonl: Path,
    myeongni_per_date_jsonl: Path,
    rebuild_science: bool,
) -> dict[str, Any]:
    if rebuild_science or not DEFAULT_SCIENCE_JSONL_KOSPI.is_file():
        _ensure_science_jsonl(
            instrument="kospi",
            csv_path=v1.KOSPI_CSV,
            out_path=DEFAULT_SCIENCE_JSONL_KOSPI,
            date_from=date_from,
            date_to=date_to,
            apply_overnight=True,
        )

    sidecar_doc = export_humanist_jsonl_from_sidecar(
        sidecar_path=sidecar_path, instrument="kospi"
    ) if sidecar_path and sidecar_path.is_file() else {"myeongni_rows": [], "sasang_rows": [], "n_eval_dates": 0}
    if sidecar_doc.get("myeongni_rows") or sidecar_doc.get("sasang_rows"):
        _write_jsonl(sidecar_doc["myeongni_rows"], DEFAULT_MYEONGNI_OUT)
        _write_jsonl(sidecar_doc["sasang_rows"], DEFAULT_SASANG_OUT)

    common_holdout = dict(
        train_from=date_from,
        train_to=train_to,
        holdout_from=holdout_from,
        holdout_to=holdout_to,
        neutral_bps=5.0,
        logos_lens=DEFAULT_LOGOS_LENS,
        rebuild_science=False,
    )

    stub_doc = run_holdout_bundle(
        myeongni_jsonl=DEFAULT_MYEONGNI_JSONL,
        sasang_jsonl=DEFAULT_SASANG_JSONL,
        **common_holdout,
    )
    sidecar_doc_holdout = run_holdout_bundle(
        myeongni_jsonl=DEFAULT_MYEONGNI_OUT if (DEFAULT_MYEONGNI_OUT.is_file()) else DEFAULT_MYEONGNI_JSONL,
        sasang_jsonl=DEFAULT_SASANG_OUT if (DEFAULT_SASANG_OUT.is_file()) else DEFAULT_SASANG_JSONL,
        **common_holdout,
    )
    market_doc = run_holdout_bundle(
        myeongni_jsonl=DEFAULT_MYEONGNI_JSONL,
        sasang_jsonl=market_sasang_jsonl,
        **common_holdout,
    )
    full_doc = run_holdout_bundle(
        myeongni_jsonl=myeongni_per_date_jsonl
        if myeongni_per_date_jsonl.is_file()
        else DEFAULT_MYEONGNI_JSONL,
        sasang_jsonl=market_sasang_jsonl,
        **common_holdout,
    )

    stub_sum = _summarize_holdout(stub_doc, "calendar_stub_202606")
    sidecar_sum = _summarize_holdout(sidecar_doc_holdout, "sidecar_dated_snapshot")
    market_sum = _summarize_holdout(market_doc, "market_sasang_v2_per_date")
    full_sum = _summarize_holdout(full_doc, "full_deterministic_humanist")

    stub_u = stub_sum.get("holdout_uplift_soft")
    side_u = sidecar_sum.get("holdout_uplift_soft")
    market_u = market_sum.get("holdout_uplift_soft")
    full_u = full_sum.get("holdout_uplift_soft")
    delta_side = round(float(side_u) - float(stub_u), 4) if side_u is not None and stub_u is not None else None
    delta_market = round(float(market_u) - float(stub_u), 4) if market_u is not None and stub_u is not None else None
    delta_full = round(float(full_u) - float(stub_u), 4) if full_u is not None and stub_u is not None else None

    return {
        "schema": "science_core_humanist_source_ab_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "windows": {
            "train": {"from": date_from, "to": train_to},
            "holdout": {"from": holdout_from, "to": holdout_to},
        },
        "sidecar_export": {
            "sidecar_json": str(sidecar_path).replace("\\", "/") if sidecar_path else None,
            "n_eval_dates": sidecar_doc.get("n_eval_dates"),
            "date_min": sidecar_doc.get("date_min"),
            "date_max": sidecar_doc.get("date_max"),
            "myeongni_jsonl": str(DEFAULT_MYEONGNI_OUT.relative_to(ROOT)).replace("\\", "/"),
            "sasang_jsonl": str(DEFAULT_SASANG_OUT.relative_to(ROOT)).replace("\\", "/"),
        },
        "market_sasang_jsonl": str(market_sasang_jsonl.relative_to(ROOT)).replace("\\", "/")
        if market_sasang_jsonl.is_relative_to(ROOT)
        else str(market_sasang_jsonl),
        "myeongni_per_date_jsonl": str(myeongni_per_date_jsonl.relative_to(ROOT)).replace("\\", "/")
        if myeongni_per_date_jsonl.is_relative_to(ROOT)
        else str(myeongni_per_date_jsonl),
        "arms": {
            "calendar_stub": stub_sum,
            "sidecar_dated": sidecar_sum,
            "market_sasang_v2": market_sum,
            "full_deterministic_humanist": full_sum,
        },
        "delta_sidecar_minus_stub": {"holdout_uplift_soft": delta_side},
        "delta_market_sasang_minus_stub": {"holdout_uplift_soft": delta_market},
        "delta_full_deterministic_minus_stub": {"holdout_uplift_soft": delta_full},
        "interpretation_ko": (
            "market_sasang_v2는 OHLCV/market_psych v2 per-date; calendar stub inflation 완화 목적. "
            "full_deterministic_humanist = manseryeok session myeongni + market sasang (둘 다 stub:false). "
            "sidecar export는 score 패널 날짜 커버에 종속. composite attach 자동 승격 없음."
        ),
        "promotion_gate": {
            "track_a_ready": False,
            "live_trading_ready": False,
            "research_lane_status": "observe_only",
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", type=str, default="2026-01-01")
    ap.add_argument("--date-to", type=str, default="2026-06-08")
    ap.add_argument("--train-to", type=str, default="2026-04-30")
    ap.add_argument("--holdout-from", type=str, default="2026-05-01")
    ap.add_argument("--holdout-to", type=str, default="2026-06-08")
    ap.add_argument("--sidecar-json", type=Path, default=DEFAULT_EXTENDED_SIDECAR)
    ap.add_argument("--market-sasang-jsonl", type=Path, default=DEFAULT_MARKET_SASANG_JSONL)
    ap.add_argument("--myeongni-per-date-jsonl", type=Path, default=DEFAULT_MYEONGNI_PER_DATE_JSONL)
    ap.add_argument("--rebuild-science", action="store_true")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--artifact-output", type=Path, default=ART_OUT)
    args = ap.parse_args(argv)

    doc = run_ab(
        date_from=args.date_from,
        date_to=args.date_to,
        train_to=args.train_to,
        holdout_from=args.holdout_from,
        holdout_to=args.holdout_to,
        sidecar_path=args.sidecar_json if args.sidecar_json.is_file() else None,
        market_sasang_jsonl=args.market_sasang_jsonl,
        myeongni_per_date_jsonl=args.myeongni_per_date_jsonl,
        rebuild_science=args.rebuild_science,
    )
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.artifact_output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(payload, encoding="utf-8")
    args.artifact_output.write_text(payload, encoding="utf-8")

    d = doc.get("delta_market_sasang_minus_stub") or {}
    print(f"WROTE: {args.output.resolve()} market_uplift_delta={d.get('holdout_uplift_soft')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
