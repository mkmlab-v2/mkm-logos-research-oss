#!/usr/bin/env python3
"""Compare Sasang 4-agent real-slice vs KOSPI timeseries probes [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
REAL_SLICE = ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_real_slice_latest.json"
TIMESERIES = ROOT / "docs/final/artifacts/sasang_4agent_collision_btrack_protocol_timeseries_kospi_latest.json"
OUT = ROOT / "reports/sasang_4agent_dual_probe_compare_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _probe_summary(doc: dict[str, Any]) -> dict[str, Any]:
    exp = doc.get("experiment") if isinstance(doc.get("experiment"), dict) else {}
    res = doc.get("results") if isinstance(doc.get("results"), dict) else {}
    hint = doc.get("promotion_gate_hint") if isinstance(doc.get("promotion_gate_hint"), dict) else {}
    return {
        "data_mode": exp.get("data_mode"),
        "ticks": exp.get("ticks"),
        "mdd_reduction_abs": res.get("mdd_reduction_abs"),
        "hold_ratio": res.get("hold_ratio"),
        "p_bootstrap": res.get("mdd_reduction_p_value_bootstrap"),
        "p_permutation": res.get("mdd_reduction_p_value_permutation"),
        "promotion_hint": hint.get("decision"),
    }


def build() -> dict[str, Any]:
    real = _load(REAL_SLICE)
    ts = _load(TIMESERIES)
    real_sum = _probe_summary(real)
    ts_sum = _probe_summary(ts)

    both_present = (
        real.get("schema") == "sasang_4agent_collision_btrack_protocol_v1"
        and ts.get("schema") == "sasang_4agent_collision_btrack_protocol_v1"
    )
    mdd_real = float(real_sum.get("mdd_reduction_abs") or 0.0)
    mdd_ts = float(ts_sum.get("mdd_reduction_abs") or 0.0)
    delta_mdd = mdd_ts - mdd_real

    compare_ok = (
        both_present
        and real_sum.get("data_mode") == "real_slice_backtest_adapter"
        and ts_sum.get("data_mode") == "timeseries_file_adapter"
        and int(real_sum.get("ticks") or 0) >= 40
        and int(ts_sum.get("ticks") or 0) >= 40
    )

    return {
        "schema": "sasang_4agent_dual_probe_compare_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "compare_ok": compare_ok,
        "real_slice": real_sum,
        "timeseries_kospi": ts_sum,
        "delta": {
            "mdd_reduction_abs_timeseries_minus_real_slice": round(delta_mdd, 6),
            "hold_ratio_delta": round(
                float(ts_sum.get("hold_ratio") or 0.0) - float(real_sum.get("hold_ratio") or 0.0),
                6,
            ),
            "promotion_hint_agree": real_sum.get("promotion_hint") == ts_sum.get("promotion_hint"),
        },
        "artifact_paths": {
            "real_slice": str(REAL_SLICE).replace("\\", "/"),
            "timeseries_kospi": str(TIMESERIES).replace("\\", "/"),
        },
        "reproduce": "py scripts/build_sasang_4agent_dual_probe_compare_report_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["compare_ok"], "delta_mdd": doc["delta"]["mdd_reduction_abs_timeseries_minus_real_slice"]}))
    return 0 if doc["compare_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
