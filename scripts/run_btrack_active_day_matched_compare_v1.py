#!/usr/bin/env python3
"""[HYPO] Compare prophecy lanes on MS-active days only (fair subset on anchor 30d)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_ANCHOR = ROOT / "reports/btrack_prophecy_score_30d_frozen_kpi_a_v1.json"
DEFAULT_V1_SCORE = ROOT / "reports/btrack_prophecy_score_v1_prod_perdate_30d_v1.json"
DEFAULT_MS_PER_DATE = ROOT / "reports/btrack_lens_combo_ms_per_date_anchor_v1.json"
DEFAULT_OUT = ROOT / "reports/btrack_active_day_matched_compare_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(p.resolve())


def _btc_actual_by_date(score: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in score.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "").lower() != "btc":
            continue
        ed = str(row.get("eval_date") or "")[:10]
        if ed:
            out[ed] = str(row.get("actual_direction") or "").strip().lower()
    return out


def _btc_pred_by_date(score: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in score.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "").lower() != "btc":
            continue
        ed = str(row.get("eval_date") or "")[:10]
        if ed:
            out[ed] = str(row.get("predicted_direction") or "").strip().lower()
    return out


def _pred_from_per_date(doc: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for row in doc.get("rows") or []:
        if not isinstance(row, dict):
            continue
        if str(row.get("instrument") or "btc").lower() != "btc":
            continue
        ed = str(row.get("eval_date") or "")[:10]
        if ed:
            out[ed] = str(row.get("predicted_direction") or "").strip().lower()
    return out


def _lane_hits(
    dates: list[str],
    actual: dict[str, str],
    pred: dict[str, str],
    *,
    require_directional: bool,
) -> dict[str, Any]:
    hits = 0
    n = 0
    neutral_skipped = 0
    disagreements_with_actual: list[dict[str, str]] = []
    for ed in dates:
        p = pred.get(ed, "neutral")
        if require_directional and p not in ("bull", "bear"):
            neutral_skipped += 1
            continue
        a = actual.get(ed, "")
        if not a:
            continue
        n += 1
        if p == a:
            hits += 1
        else:
            disagreements_with_actual.append({"eval_date": ed, "pred": p, "actual": a})
    rate = round(hits / n, 6) if n else None
    return {
        "n_days": n,
        "hits": hits,
        "directional_hit_rate": rate,
        "neutral_skipped": neutral_skipped,
        "sample_misses": disagreements_with_actual[:5],
    }


def build_compare(
    *,
    anchor_score: Path,
    v1_score: Path,
    ms_per_date: Path,
    frozen_score: Path | None = None,
) -> dict[str, Any]:
    anchor = _load(anchor_score)
    actual = _btc_actual_by_date(anchor)
    panel_dates = sorted(actual.keys())

    frozen_doc = _load(frozen_score) if frozen_score and frozen_score.is_file() else anchor
    frozen_pred = _btc_pred_by_date(frozen_doc)

    v1_doc = _load(v1_score)
    v1_pred = _btc_pred_by_date(v1_doc)

    ms_doc = _load(ms_per_date)
    ms_pred = _pred_from_per_date(ms_doc)

    ms_active_dates = [d for d in panel_dates if ms_pred.get(d) in ("bull", "bear")]
    v1_active_dates = [d for d in panel_dates if v1_pred.get(d) in ("bull", "bear")]
    overlap = sorted(set(ms_active_dates) & set(v1_active_dates))

    lanes = {
        "frozen_kpi_a_on_ms_active": _lane_hits(
            ms_active_dates, actual, frozen_pred, require_directional=False
        ),
        "v1_per_date_on_ms_active": _lane_hits(
            ms_active_dates, actual, v1_pred, require_directional=False
        ),
        "ms_on_ms_active": _lane_hits(
            ms_active_dates, actual, ms_pred, require_directional=False
        ),
        "v1_per_date_on_v1_active": _lane_hits(
            v1_active_dates, actual, v1_pred, require_directional=True
        ),
        "ms_on_overlap_v1_and_ms_active": _lane_hits(
            overlap, actual, ms_pred, require_directional=False
        ),
        "v1_on_overlap_v1_and_ms_active": _lane_hits(
            overlap, actual, v1_pred, require_directional=False
        ),
    }

    return {
        "schema": "btrack_active_day_matched_compare_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "panel": {
            "anchor_score": _rel(anchor_score),
            "n_panel_days": len(panel_dates),
            "ms_active_days": len(ms_active_dates),
            "v1_active_days": len(v1_active_dates),
            "overlap_active_days": len(overlap),
        },
        "inputs": {
            "v1_score": _rel(v1_score),
            "ms_per_date": _rel(ms_per_date),
            "frozen_score": _rel(frozen_score) if frozen_score else _rel(anchor_score),
        },
        "lanes": lanes,
        "operator_lines": [
            "- [MKM-MATCHED] MS-active subset only — not comparable to full-panel 56.7% without label.",
            "- [MKM-MATCHED] Compare v1_on_ms_active vs ms_on_ms_active before MS-only promotion narrative.",
            "- [MKM-MATCHED] Track A / frozen headline unchanged; research_only.",
        ],
    }


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--anchor-score", type=Path, default=DEFAULT_ANCHOR)
    ap.add_argument("--v1-score", type=Path, default=DEFAULT_V1_SCORE)
    ap.add_argument("--ms-per-date", type=Path, default=DEFAULT_MS_PER_DATE)
    ap.add_argument("--frozen-score", type=Path, default=DEFAULT_ANCHOR)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    for label, p in (
        ("anchor", args.anchor_score),
        ("v1", args.v1_score),
        ("ms", args.ms_per_date),
    ):
        if not p.is_file():
            print(f"MISSING {label}: {p}", file=sys.stderr)
            return 1

    doc = build_compare(
        anchor_score=args.anchor_score,
        v1_score=args.v1_score,
        ms_per_date=args.ms_per_date,
        frozen_score=args.frozen_score,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()}")
    ms = doc["lanes"]["ms_on_ms_active"]
    v1 = doc["lanes"]["v1_per_date_on_ms_active"]
    print(
        f"MS-active n={doc['panel']['ms_active_days']}: "
        f"MS={ms['directional_hit_rate']} v1={v1['directional_hit_rate']} "
        f"frozen={doc['lanes']['frozen_kpi_a_on_ms_active']['directional_hit_rate']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
