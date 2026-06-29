#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Compare snapshot vs walk-forward KOSPI lens ablation [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SNAPSHOT = ROOT / "reports/kospi_lens_ablation_backtest_latest.json"
DEFAULT_WALKFORWARD = ROOT / "reports/kospi_lens_ablation_backtest_walkforward_latest.json"
DEFAULT_WALKFORWARD_MACRO = (
    ROOT / "reports/kospi_lens_ablation_backtest_walkforward_macro_latest.json"
)
DEFAULT_OUT = ROOT / "reports/kospi_lens_ablation_snapshot_vs_walkforward_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _arm_rows(doc: dict[str, Any]) -> list[dict[str, Any]]:
    return list(doc.get("ranked_arms") or doc.get("arms") or [])


def _arm_metrics(row: dict[str, Any]) -> dict[str, Any]:
    metrics = row.get("metrics") or {}
    return metrics if isinstance(metrics, dict) else {}


def _arm_hr(doc: dict[str, Any], arm_id: str) -> float | None:
    for row in _arm_rows(doc):
        if row.get("arm_id") == arm_id:
            m = _arm_metrics(row)
            return m.get("soft_hit_rate", row.get("soft_hit_rate"))
    return None


def _rank_arms(doc: dict[str, Any]) -> list[dict[str, Any]]:
    arms = _arm_rows(doc)
    arms.sort(
        key=lambda r: float(_arm_metrics(r).get("soft_hit_rate") or r.get("soft_hit_rate") or 0),
        reverse=True,
    )
    return [
        {
            "arm_id": r.get("arm_id"),
            "soft_hit_rate": _arm_metrics(r).get("soft_hit_rate", r.get("soft_hit_rate")),
            "n_scored": _arm_metrics(r).get("n_scored", r.get("n_scored")),
            "pred_neutral_rate": r.get("pred_neutral_rate"),
        }
        for r in arms
    ]


def build_summary(
    snapshot: dict[str, Any],
    walkforward: dict[str, Any],
    *,
    walkforward_macro: dict[str, Any] | None = None,
) -> dict[str, Any]:
    arms = [
        "lens3_runtime",
        "sasang_myeongni_only",
        "three_lens_runtime",
        "lens3_4ai_overlay",
    ]
    deltas: list[dict[str, Any]] = []
    for arm in arms:
        snap_hr = _arm_hr(snapshot, arm)
        wf_hr = _arm_hr(walkforward, arm)
        macro_hr = _arm_hr(walkforward_macro, arm) if walkforward_macro else None
        deltas.append(
            {
                "arm_id": arm,
                "snapshot_soft_hr": snap_hr,
                "walkforward_soft_hr": wf_hr,
                "walkforward_minus_snapshot_pp": (
                    round((wf_hr - snap_hr) * 100, 2)
                    if snap_hr is not None and wf_hr is not None
                    else None
                ),
                "walkforward_macro_soft_hr": macro_hr,
            }
        )

    overlay_snap = _arm_hr(snapshot, "lens3_4ai_overlay")
    overlay_wf = _arm_hr(walkforward, "lens3_4ai_overlay")
    lens3_snap = _arm_hr(snapshot, "lens3_runtime")
    lens3_wf = _arm_hr(walkforward, "lens3_runtime")
    overlay_uplift_snap = (
        round((overlay_snap - lens3_snap) * 100, 2)
        if overlay_snap is not None and lens3_snap is not None
        else None
    )
    overlay_uplift_wf = (
        round((overlay_wf - lens3_wf) * 100, 2)
        if overlay_wf is not None and lens3_wf is not None
        else None
    )

    verdict_lines = [
        "Snapshot rankings are not promotion-grade: static lens arms can show fixed-direction bias.",
        f"4AI overlay uplift snapshot {overlay_uplift_snap}pp vs walk-forward {overlay_uplift_wf}pp.",
        "Walk-forward SSOT for WATCH_ABLATION_RUN; hold evolution promotion_ready=false.",
    ]
    if walkforward_macro:
        verdict_lines.append(
            "Walk-forward+macro variant included; logos/field still global snapshot."
        )

    return {
        "schema": "kospi_lens_ablation_snapshot_vs_walkforward_v1",
        "generated_at_utc": _utc_now(),
        "boundary_ack": "[HYPO][research_only]",
        "snapshot_ranking": _rank_arms(snapshot),
        "walkforward_ranking": _rank_arms(walkforward),
        "walkforward_macro_ranking": (
            _rank_arms(walkforward_macro) if walkforward_macro else None
        ),
        "arm_deltas": deltas,
        "overlay_uplift_pp": {
            "snapshot": overlay_uplift_snap,
            "walkforward": overlay_uplift_wf,
        },
        "verdict_lines": verdict_lines,
        "sources": {
            "snapshot": str(DEFAULT_SNAPSHOT),
            "walkforward": str(DEFAULT_WALKFORWARD),
            "walkforward_macro": (
                str(DEFAULT_WALKFORWARD_MACRO) if walkforward_macro else None
            ),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--snapshot", type=Path, default=DEFAULT_SNAPSHOT)
    ap.add_argument("--walkforward", type=Path, default=DEFAULT_WALKFORWARD)
    ap.add_argument("--walkforward-macro", type=Path, default=DEFAULT_WALKFORWARD_MACRO)
    ap.add_argument("--skip-macro", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.snapshot.is_file():
        print(f"Missing snapshot: {args.snapshot}", file=sys.stderr)
        return 2
    if not args.walkforward.is_file():
        print(f"Missing walkforward: {args.walkforward}", file=sys.stderr)
        return 2

    wf_macro = None
    if not args.skip_macro and args.walkforward_macro.is_file():
        wf_macro = _load(args.walkforward_macro)

    doc = build_summary(_load(args.snapshot), _load(args.walkforward), walkforward_macro=wf_macro)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    art = ROOT / "docs/final/artifacts/kospi_lens_ablation_snapshot_vs_walkforward_latest.json"
    art.parent.mkdir(parents=True, exist_ok=True)
    art.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"out": str(args.out), "verdict": doc["verdict_lines"][:2]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
