#!/usr/bin/env python3
"""[HYPO] Aggregate anchor-30d hit-rate eval JSONs into one comparison snapshot."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/btrack_anchor_panel_hit_rate_snapshot_v1_latest.json"

DEFAULT_EVALS: list[tuple[str, Path]] = [
    ("frozen_kpi_a", ROOT / "reports/prophecy_hit_rate_eval_30d_frozen_kpi_a_v1.json"),
    ("v1_per_date", ROOT / "reports/prophecy_hit_rate_eval_v1_prod_perdate_30d_v1.json"),
    ("v1_shadow", ROOT / "reports/prophecy_hit_rate_eval_v1_shadow_anchor_30d_v1.json"),
    ("ms_myeongni_sasang", ROOT / "reports/prophecy_hit_rate_eval_ms_anchor_v1_v2.json"),
    (
        "hybrid_ms_when_active_else_v1",
        ROOT / "reports/btrack_v1_ms_hybrid_work/ms_when_active_else_v1/eval.json",
    ),
    (
        "hybrid_agree_or_ms_else_v1",
        ROOT / "reports/btrack_v1_ms_hybrid_work/agree_or_ms_else_v1/eval.json",
    ),
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def _slice_eval(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"present": False, "path": _rel(path)}
    doc = json.loads(path.read_text(encoding="utf-8"))
    m = doc.get("metrics") or {}
    return {
        "present": True,
        "path": _rel(path),
        "all_rows": m.get("price_directional_hit_rate"),
        "dir_only": m.get("price_hit_rate_on_directional_calls"),
        "n": m.get("n_evaluated"),
        "calls": m.get("n_directional_calls"),
        "neutral": m.get("n_neutral_predictions"),
        "scoring_mode": m.get("scoring_mode"),
        "headline_instrument": m.get("headline_instrument"),
    }


def build_snapshot(extra: list[tuple[str, Path]] | None = None) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for label, path in list(DEFAULT_EVALS) + list(extra or []):
        row = {"label": label, **_slice_eval(path)}
        rows.append(row)

    present = [r for r in rows if r.get("present")]
    best_all = max(
        (r for r in present if r.get("all_rows") is not None),
        key=lambda r: float(r["all_rows"]),
        default=None,
    )
    best_dir = max(
        (r for r in present if r.get("dir_only") is not None and (r.get("calls") or 0) >= 10),
        key=lambda r: float(r["dir_only"]),
        default=None,
    )

    return {
        "schema": "btrack_anchor_panel_hit_rate_snapshot_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panel": "anchor_30d_btc_2026-04-02_2026-05-15",
        "lanes": rows,
        "best_all_rows": {
            "label": best_all.get("label") if best_all else None,
            "rate": best_all.get("all_rows") if best_all else None,
        },
        "best_dir_only_min_10_calls": {
            "label": best_dir.get("label") if best_dir else None,
            "rate": best_dir.get("dir_only") if best_dir else None,
            "calls": best_dir.get("calls") if best_dir else None,
        },
        "operator_lines": [
            "- [MKM-SNAPSHOT] Hit-rate only; promotion gates need walk-forward artifacts separately.",
            "- [MKM-SNAPSHOT] frozen_kpi_a is operational headline; others are research candidates.",
        ],
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build_snapshot()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    b = doc.get("best_all_rows") or {}
    print(f"BEST all-rows: {b.get('label')} {b.get('rate')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
