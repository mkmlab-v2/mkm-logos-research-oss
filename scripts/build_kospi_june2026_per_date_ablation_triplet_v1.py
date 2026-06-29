#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Snapshot vs per-date vs per-date+macro ablation triplet [HYPO][RQ-032]."""

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

from scripts.run_kospi_lens_ablation_backtest_v1 import (  # noqa: E402
    DEFAULT_MYEONGNI_JSONL,
    DEFAULT_PANEL_FULL,
    DEFAULT_SASANG_JSONL,
    KOSPI_CSV,
    _load_closes,
    _load_panel,
    _read_json,
    run_ablation,
)
from scripts.kospi_lens_per_date_static_v1 import DEFAULT_MACRO_BACKFILL_JSONL  # noqa: E402
from scripts.run_kospi_multilens_blend_backtest_v1 import EVOLUTION_RULES  # noqa: E402

DEFAULT_OUT = ROOT / "reports/kospi_june2026_per_date_ablation_triplet_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _best_soft(doc: dict[str, Any]) -> float | None:
    best = doc.get("best_arm") or {}
    m = best.get("metrics") if isinstance(best.get("metrics"), dict) else {}
    v = m.get("soft_hit_rate")
    return float(v) if v is not None else None


def _arm_soft(doc: dict[str, Any], arm_id: str) -> float | None:
    for row in doc.get("arms") or []:
        if str(row.get("arm_id")) == arm_id:
            m = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
            v = m.get("soft_hit_rate")
            return float(v) if v is not None else None
    return None


def build_triplet(
    *,
    date_from: str,
    date_to: str,
    panel_csv: Path,
    kospi_csv: Path,
) -> dict[str, Any]:
    rules = _read_json(EVOLUTION_RULES)
    panel = _load_panel(panel_csv)
    closes = _load_closes(kospi_csv)
    neutral_bps = float(rules.get("neutral_bps", 5.0))

    modes: list[tuple[str, dict[str, Any]]] = [
        ("snapshot", {"lens_source": "snapshot", "include_macro_per_date": False}),
        (
            "per_date_jsonl",
            {
                "lens_source": "per_date_jsonl",
                "include_macro_per_date": False,
                "myeongni_jsonl": DEFAULT_MYEONGNI_JSONL,
                "sasang_jsonl": DEFAULT_SASANG_JSONL,
            },
        ),
        (
            "per_date_jsonl_macro",
            {
                "lens_source": "per_date_jsonl",
                "include_macro_per_date": True,
                "myeongni_jsonl": DEFAULT_MYEONGNI_JSONL,
                "sasang_jsonl": DEFAULT_SASANG_JSONL,
                "macro_jsonl": DEFAULT_MACRO_BACKFILL_JSONL,
            },
        ),
    ]

    results: dict[str, Any] = {}
    for mode_id, kwargs in modes:
        doc = run_ablation(
            panel_by_date=panel,
            closes=closes,
            date_from=date_from,
            date_to=date_to,
            rules=rules,
            neutral_bps=neutral_bps,
            **kwargs,
        )
        results[mode_id] = {
            "best_arm_id": (doc.get("best_arm") or {}).get("arm_id"),
            "best_soft_hit_rate": _best_soft(doc),
            "lens3_runtime_soft": _arm_soft(doc, "lens3_runtime"),
            "lens3_4ai_overlay_soft": _arm_soft(doc, "lens3_4ai_overlay"),
            "four_ai_overlay_uplift_pp": doc.get("four_ai_overlay_uplift_pp_vs_lens3_runtime"),
            "n_calendar_days": (doc.get("window") or {}).get("n_calendar_days"),
        }

    snap_lens3 = (results.get("snapshot") or {}).get("lens3_runtime_soft")
    pd_lens3 = (results.get("per_date_jsonl") or {}).get("lens3_runtime_soft")
    pdm_lens3 = (results.get("per_date_jsonl_macro") or {}).get("lens3_runtime_soft")

    return {
        "schema": "kospi_june2026_per_date_ablation_triplet_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "rq_pointer": "RQ-032",
        "window": {"date_from": date_from, "date_to": date_to},
        "modes": results,
        "lens3_runtime_deltas_pp": {
            "per_date_minus_snapshot": round(float(pd_lens3 or 0) - float(snap_lens3 or 0), 4)
            if pd_lens3 is not None and snap_lens3 is not None
            else None,
            "per_date_macro_minus_per_date": round(float(pdm_lens3 or 0) - float(pd_lens3 or 0), 4)
            if pdm_lens3 is not None and pd_lens3 is not None
            else None,
        },
        "logos_field_note_ko": "logos/field는 여전히 global snapshot — per-date logos는 미구현([HYPO] 후속).",
        "verdict_ko": "per-date myeongni+sasang(+macro) triplet shadow — apply·Track A 승격 금지.",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--date-from", default="2025-11-01")
    ap.add_argument("--date-to", default="2026-05-30")
    ap.add_argument("--panel-csv", type=Path, default=DEFAULT_PANEL_FULL)
    ap.add_argument("--kospi-csv", type=Path, default=KOSPI_CSV)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    if not args.panel_csv.is_file():
        raise SystemExit(f"Missing panel: {args.panel_csv}")

    doc = build_triplet(
        date_from=args.date_from,
        date_to=args.date_to,
        panel_csv=args.panel_csv,
        kospi_csv=args.kospi_csv,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    d = doc.get("lens3_runtime_deltas_pp") or {}
    print(
        f"WROTE: {args.output.resolve()} "
        f"pd-snap={d.get('per_date_minus_snapshot')} "
        f"macro-pd={d.get('per_date_macro_minus_per_date')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
