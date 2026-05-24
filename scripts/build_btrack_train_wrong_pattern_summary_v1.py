#!/usr/bin/env python3
"""[HYPO] Summarize 180d train_wrong vs holdout7 wrong_dir feature patterns (CSV + JSON)."""
from __future__ import annotations

import argparse
import csv
import json
import statistics
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.btrack_wrong_dir_holdout_core_v1 import wrong_dir_cohort_with_auxiliary

DEFAULT_DUMP = ROOT / "reports/btrack_wrong_dir_holdout_features_180d_v1_latest.json"
DEFAULT_CSV = ROOT / "reports/btrack_train_wrong_pattern_summary_v1_latest.csv"
DEFAULT_OUT = ROOT / "reports/btrack_train_wrong_pattern_summary_v1_latest.json"
DEFAULT_GATE = ROOT / "reports/btrack_holdout_gate_candidate_v1_latest.json"
DEFAULT_PER_180 = ROOT / "reports/btrack_ensemble_per_date_directions_180d_v1_latest.json"

DEFAULT_GATE_LAYER: dict[str, Any] = {
    "enabled": True,
    "action": "force_neutral",
    "apply_when": {
        "holdout_only": True,
        "preliminary_bull": True,
        "overnight_negative_or_positive": True,
    },
}


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _f(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _cohort_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"n": 0}
    ovn = [_f(r.get("overnight_return")) for r in rows]
    prp = [_f(r.get("prior_range_position")) for r in rows]
    ldr = [_f(r.get("last_daily_return")) for r in rows]
    ovn = [x for x in ovn if x is not None]
    prp = [x for x in prp if x is not None]
    ldr = [x for x in ldr if x is not None]
    return {
        "n": len(rows),
        "overnight_negative_pct": round(sum(1 for x in ovn if x < 0) / len(ovn), 4) if ovn else None,
        "overnight_positive_pct": round(sum(1 for x in ovn if x > 0) / len(ovn), 4) if ovn else None,
        "prior_range_low_pct": round(sum(1 for x in prp if x < 0.35) / len(prp), 4) if prp else None,
        "vol_high_pct": round(sum(1 for r in rows if r.get("vol_regime_high")) / len(rows), 4),
        "last_ret_negative_pct": round(sum(1 for x in ldr if x < 0) / len(ldr), 4) if ldr else None,
        "price_lens_bull_pct": round(
            sum(
                1
                for r in rows
                if (_f(r.get("price_lens_score")) or _f((r.get("lens_values") or {}).get("price", {}).get("score")) or 0)
                > 0.03
            )
            / len(rows),
            4,
        ),
        "overnight_mean": round(statistics.mean(ovn), 6) if ovn else None,
        "prior_range_mean": round(statistics.mean(prp), 6) if prp else None,
    }


def _gate_layer(gate_doc: dict[str, Any] | None) -> dict[str, Any]:
    if gate_doc and isinstance(gate_doc.get("candidate_layer"), dict):
        cl = gate_doc["candidate_layer"]
        return {
            "enabled": cl.get("enabled", True),
            "action": cl.get("action", "force_neutral"),
            "apply_when": cl.get("apply_when") or DEFAULT_GATE_LAYER["apply_when"],
        }
    return dict(DEFAULT_GATE_LAYER)


def _insights(holdout: list[dict], train: list[dict], gate_sim: dict[str, Any]) -> list[str]:
    lines: list[str] = []
    h = _cohort_stats(holdout)
    t = _cohort_stats(train)
    if h.get("n"):
        lines.append(
            f"- [MKM-TRAIN-WRONG-PAT] holdout7: price_bull={h.get('price_lens_bull_pct')} "
            f"ovn_neg={h.get('overnight_negative_pct')} ovn_pos={h.get('overnight_positive_pct')} "
            f"last_ret_neg={h.get('last_ret_negative_pct')}"
        )
    if t.get("n"):
        lines.append(
            f"- [MKM-TRAIN-WRONG-PAT] train_wrong: price_bull={t.get('price_lens_bull_pct')} "
            f"ovn_neg={t.get('overnight_negative_pct')} ovn_pos={t.get('overnight_positive_pct')} "
            f"last_ret_neg={t.get('last_ret_negative_pct')}"
        )
    if gate_sim:
        lines.append(
            f"- [MKM-TRAIN-WRONG-PAT] gate={gate_sim.get('slug')} holdout7_neutralized="
            f"{gate_sim.get('holdout_neutralized')}/{gate_sim.get('holdout_n')} "
            f"train_wrong_neutralized={gate_sim.get('train_neutralized')}/{gate_sim.get('train_n')} "
            f"(holdout_only boundary)."
        )
    lines.append(
        "- [MKM-TRAIN-WRONG-PAT] advisory/ops hints only; holdout gate does not fix headline ALERT_1."
    )
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dump", type=Path, default=DEFAULT_DUMP)
    ap.add_argument("--csv-out", type=Path, default=DEFAULT_CSV)
    ap.add_argument("--json-out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--gate-manifest", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--per-date-180", type=Path, default=DEFAULT_PER_180)
    args = ap.parse_args()

    if not args.dump.is_file():
        print(f"Missing dump: {args.dump}", file=sys.stderr)
        return 2

    dump = _load(args.dump)
    holdout_dates = list(dump.get("holdout_7_dates") or [])
    rows = [r for r in dump.get("rows") or [] if isinstance(r, dict)]
    wrong = [r for r in rows if r.get("is_wrong_direction")]
    holdout = [r for r in wrong if r.get("is_holdout_7")]
    train = [r for r in wrong if not r.get("is_holdout_7")]
    hits = [r for r in rows if r.get("is_hit_all_rows")]

    gate_doc = _load(args.gate_manifest) if args.gate_manifest.is_file() else None
    layer = _gate_layer(gate_doc)
    gate_slug = (gate_doc or {}).get("candidate_layer", {}).get("slug") or "holdout_ovn_signed_bull"
    gate_sim: dict[str, Any] = {}
    if args.per_date_180.is_file() and holdout_dates:
        per180 = _load(args.per_date_180)
        hwd = wrong_dir_cohort_with_auxiliary(per180, dump, holdout_dates, layer, holdout_only=True)
        twd = wrong_dir_cohort_with_auxiliary(per180, dump, holdout_dates, layer, holdout_only=False)
        gate_sim = {
            "slug": gate_slug,
            "holdout_n": hwd.get("n_wrong_dir_days"),
            "holdout_neutralized": hwd.get("neutralized"),
            "train_n": twd.get("n_wrong_dir_days"),
            "train_neutralized": twd.get("neutralized"),
            "train_leakage_ok": int(twd.get("neutralized") or 0) == 0,
        }

    csv_fields = [
        "eval_date",
        "cohort",
        "predicted_direction",
        "actual_direction",
        "preliminary_direction",
        "overnight_return",
        "prior_range_position",
        "last_daily_return",
        "realized_vol_5d",
        "vol_regime_high",
        "price_lens_score",
        "weighted_score",
        "is_holdout_7",
    ]

    def _csv_row(r: dict[str, Any], cohort: str) -> dict[str, Any]:
        lv = r.get("lens_values") if isinstance(r.get("lens_values"), dict) else {}
        price = lv.get("price") if isinstance(lv.get("price"), dict) else {}
        return {
            "eval_date": r.get("eval_date"),
            "cohort": cohort,
            "predicted_direction": r.get("predicted_direction"),
            "actual_direction": r.get("actual_direction"),
            "preliminary_direction": r.get("preliminary_direction"),
            "overnight_return": r.get("overnight_return"),
            "prior_range_position": r.get("prior_range_position"),
            "last_daily_return": r.get("last_daily_return"),
            "realized_vol_5d": r.get("realized_vol_5d"),
            "vol_regime_high": r.get("vol_regime_high"),
            "price_lens_score": price.get("score") or r.get("price_lens_score"),
            "weighted_score": r.get("weighted_score"),
            "is_holdout_7": r.get("is_holdout_7"),
        }

    args.csv_out.parent.mkdir(parents=True, exist_ok=True)
    with args.csv_out.open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=csv_fields)
        w.writeheader()
        for r in holdout:
            w.writerow(_csv_row(r, "holdout7_wrong_dir"))
        for r in train:
            w.writerow(_csv_row(r, "train_wrong_dir"))
        for r in hits[:20]:
            w.writerow(_csv_row(r, "hit_sample"))

    report = {
        "schema": "btrack_train_wrong_pattern_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "source_dump": str(args.dump),
        "csv_path": str(args.csv_out),
        "holdout_7_wrong_dir": _cohort_stats(holdout),
        "train_wrong_dir": _cohort_stats(train),
        "contrast_hit_sample_n20": _cohort_stats(hits[:20]),
        "holdout_gate_simulation": gate_sim,
        "recommended_boundary": {
            "apply_holdout_gate_to": "holdout_7_dates_only",
            "do_not_apply_to_train_wrong": gate_sim.get("train_leakage_ok", True),
            "rationale_ko": "train_wrong는 패턴이 혼합; holdout7은 OVN 부호 무관 bull-trap. 게이트는 headline 미개선.",
        },
        "insight_lines": [],
        "operator_lines": [],
    }
    report["insight_lines"] = _insights(holdout, train, gate_sim)
    report["operator_lines"] = [
        f"- [MKM-TRAIN-WRONG-PAT] 180d holdout7 n={len(holdout)} train_wrong n={len(train)} csv={args.csv_out.name}",
        *report["insight_lines"],
    ]
    args.json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.csv_out.resolve()}")
    print(f"WROTE: {args.json_out.resolve()}")
    for line in report["operator_lines"]:
        print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
