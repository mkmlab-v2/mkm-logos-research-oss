#!/usr/bin/env python3
"""Mean Brier score for resolved binary questions in a general_prophecy registry.

Optional --ece-bins: equal-width [0,1] bins for binary ECE (metrics.ece_binary.weighted_ece).
Per-domain_tag ECE: metrics.ece_binary_by_domain_tag when --ece-min-per-tag satisfied.

Optional auxiliary_covariates_v1.psychological_state_term (0..1): when present on resolved
rows, metrics.by_psychological_state_term_band splits at 0.5 (<= vs >), each band included
only if n >= --psy-state-min-per-band (default 2). Advisory covariate; does not alter L1 p.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_brier_eval_latest.json"
SCHEMA = "general_prophecy_brier_eval_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _last_forecast(forecasts: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not forecasts:
        return None
    sorted_f = sorted([f for f in forecasts if isinstance(f, dict)], key=lambda fc: str(fc.get("issued_at_utc") or ""))
    return sorted_f[-1] if sorted_f else None


def _parse_utc(ts: str) -> datetime | None:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return None


def _psychological_state_term(q: dict[str, Any]) -> float | None:
    aux = q.get("auxiliary_covariates_v1")
    if not isinstance(aux, dict):
        return None
    v = aux.get("psychological_state_term")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return max(0.0, min(1.0, float(v)))


def _median_int(vals: list[int]) -> float | None:
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    m = n // 2
    if n % 2 == 1:
        return float(s[m])
    return (s[m - 1] + s[m]) / 2.0


def _binary_ece_equal_width(pairs: list[tuple[float, float]], n_bins: int) -> dict[str, Any] | None:
    """Expected calibration error: sum_k (n_k/n) * |positive_rate_k - avg_confidence_k|."""
    if not pairs or n_bins < 1:
        return None
    n_total = len(pairs)
    buckets: list[list[tuple[float, float]]] = [[] for _ in range(n_bins)]
    for p, y in pairs:
        p = max(0.0, min(1.0, float(p)))
        yi = 1.0 if y >= 0.5 else 0.0
        if p >= 1.0:
            idx = n_bins - 1
        else:
            idx = min(n_bins - 1, int(p * n_bins))
        buckets[idx].append((p, yi))

    bin_rows: list[dict[str, Any]] = []
    weighted = 0.0
    lo = 0.0
    width = 1.0 / n_bins
    for i, bucket in enumerate(buckets):
        hi = lo + width
        if i == n_bins - 1:
            hi = 1.0
        nk = len(bucket)
        if nk == 0:
            bin_rows.append(
                {
                    "bin_index": i,
                    "interval_lo_inclusive": round(lo, 6),
                    "interval_hi": round(hi, 6),
                    "n": 0,
                    "avg_confidence": None,
                    "positive_rate": None,
                    "calibration_gap": None,
                }
            )
        else:
            avg_p = sum(t[0] for t in bucket) / nk
            pos_rate = sum(t[1] for t in bucket) / nk
            gap = abs(pos_rate - avg_p)
            w = nk / n_total
            weighted += w * gap
            bin_rows.append(
                {
                    "bin_index": i,
                    "interval_lo_inclusive": round(lo, 6),
                    "interval_hi": round(hi, 6),
                    "n": nk,
                    "avg_confidence": round(avg_p, 6),
                    "positive_rate": round(pos_rate, 6),
                    "calibration_gap": round(gap, 6),
                }
            )
        lo = hi

    return {
        "n_bins": n_bins,
        "scheme": "equal_width_probability",
        "weighted_ece": round(weighted, 6),
        "bins": bin_rows,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ap.add_argument(
        "--no-print-output-path",
        action="store_true",
        help="When writing JSON to --output, do not print the output path to stdout (stderr only for errors).",
    )
    ap.add_argument(
        "--no-rows",
        action="store_true",
        help="Omit per-question rows from JSON output (metrics only; smaller files).",
    )
    ap.add_argument(
        "--ece-bins",
        type=int,
        default=0,
        metavar="N",
        help="If N>0, add binary ECE over N equal-width probability bins (same resolved rows as Brier).",
    )
    ap.add_argument(
        "--ece-min-per-tag",
        type=int,
        default=5,
        metavar="M",
        help="With --ece-bins: include a domain_tag in ece_binary_by_domain_tag only if it has >= M (p,y) pairs (default 5).",
    )
    ap.add_argument(
        "--psy-state-min-per-band",
        type=int,
        default=2,
        metavar="N",
        help="Minimum resolved rows per band (psychological_state_term <=0.5 vs >0.5) to emit metrics.by_psychological_state_term_band.",
    )
    ns = ap.parse_args()
    if not ns.input.is_file():
        print(f"missing {ns.input}", file=sys.stderr)
        return 2
    doc = _load(ns.input)
    if doc.get("schema") != "general_prophecy_registry_v1":
        print("input must be general_prophecy_registry_v1", file=sys.stderr)
        return 2

    rows: list[dict[str, Any]] = []
    by_track: dict[str, list[float]] = defaultdict(list)
    by_domain_tag: dict[str, list[float]] = defaultdict(list)
    by_month: dict[str, list[float]] = defaultdict(list)
    by_resolved_month: dict[str, list[float]] = defaultdict(list)
    pending_count = 0
    overdue_count = 0
    pending_days_to_deadline: list[int] = []
    now_utc = datetime.now(timezone.utc)
    ece_pairs: list[tuple[float, float]] = []
    ece_pairs_by_tag: dict[str, list[tuple[float, float]]] = defaultdict(list)
    brier_by_psy_low: list[float] = []
    brier_by_psy_high: list[float] = []

    for q in doc.get("questions") or []:
        if not isinstance(q, dict):
            continue
        if (q.get("outcome_spec") or {}).get("kind") != "binary":
            continue
        res = q.get("resolution") or {}
        if res.get("status") == "pending":
            pending_count += 1
            ddl = q.get("resolution_deadline_utc")
            if isinstance(ddl, str):
                dt = _parse_utc(ddl)
                if dt is not None:
                    days = int((dt - now_utc).total_seconds() // 86400)
                    pending_days_to_deadline.append(days)
                    if dt < now_utc:
                        overdue_count += 1
        if res.get("status") != "resolved":
            continue
        ob = res.get("outcome_binary")
        if not isinstance(ob, bool):
            continue
        fc = _last_forecast([x for x in (q.get("forecasts") or []) if isinstance(x, dict)])
        if not fc or not isinstance(fc.get("probability_0_1"), (int, float)):
            continue
        issued_at = fc.get("issued_at_utc")
        p = float(fc["probability_0_1"])
        y = 1.0 if ob else 0.0
        if ns.ece_bins > 0:
            ece_pairs.append((p, y))
        b = (p - y) ** 2
        track = q.get("prophecy_track")
        if not isinstance(track, str) or not track.strip():
            track = "general"
        else:
            track = track.strip()
        by_track[track].append(b)
        tags = q.get("domain_tags")
        if isinstance(tags, list):
            for t in tags:
                if isinstance(t, str) and t.strip():
                    tt = t.strip()
                    by_domain_tag[tt].append(b)
                    if ns.ece_bins > 0:
                        ece_pairs_by_tag[tt].append((p, y))
        if isinstance(issued_at, str) and len(issued_at) >= 7 and issued_at[4] == "-":
            by_month[issued_at[:7]].append(b)
        resolved_at = res.get("resolved_at_utc")
        if isinstance(resolved_at, str) and len(resolved_at) >= 7 and resolved_at[4] == "-":
            by_resolved_month[resolved_at[:7]].append(b)
        psy = _psychological_state_term(q)
        if psy is not None:
            if psy <= 0.5:
                brier_by_psy_low.append(b)
            else:
                brier_by_psy_high.append(b)
        row_out: dict[str, Any] = {
            "question_id": q.get("question_id"),
            "prophecy_track": track,
            "domain_tags": [t for t in (tags or []) if isinstance(t, str)],
            "issued_at_utc": issued_at,
            "probability_0_1": p,
            "outcome_binary": ob,
            "brier_contribution": round(b, 6),
        }
        if psy is not None:
            row_out["psychological_state_term"] = round(psy, 6)
        rows.append(row_out)

    n = len(rows)
    mean_brier = round(sum(r["brier_contribution"] for r in rows) / n, 6) if n else None
    track_order = ("general", "financial", "personalized")
    by_prophecy_track: dict[str, dict[str, Any]] = {}
    for t in track_order:
        vals = by_track.get(t) or []
        if vals:
            by_prophecy_track[t] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}
    for t, vals in sorted(by_track.items()):
        if t in track_order or not vals:
            continue
        by_prophecy_track[t] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}

    by_domain_tag_metrics: dict[str, dict[str, Any]] = {}
    for tag, vals in sorted(by_domain_tag.items()):
        if vals:
            by_domain_tag_metrics[tag] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}
    by_month_metrics: dict[str, dict[str, Any]] = {}
    for month, vals in sorted(by_month.items()):
        if vals:
            by_month_metrics[month] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}
    by_resolved_month_metrics: dict[str, dict[str, Any]] = {}
    for month, vals in sorted(by_resolved_month.items()):
        if vals:
            by_resolved_month_metrics[month] = {"mean_brier_score": round(sum(vals) / len(vals), 6), "n_evaluated": len(vals)}

    metrics: dict[str, Any] = {
        "mean_brier_score": mean_brier,
        "n_evaluated": n,
        "by_prophecy_track": by_prophecy_track,
        "by_domain_tag": by_domain_tag_metrics,
        "by_month": by_month_metrics,
        "by_resolved_month": by_resolved_month_metrics,
        "pending_count": pending_count,
        "overdue_count": overdue_count,
        "median_days_to_deadline": _median_int(pending_days_to_deadline),
    }
    if ns.ece_bins > 0 and ece_pairs:
        ece_doc = _binary_ece_equal_width(ece_pairs, ns.ece_bins)
        if ece_doc:
            metrics["ece_binary"] = ece_doc
        by_tag_ece: dict[str, Any] = {}
        for tag, pairs in sorted(ece_pairs_by_tag.items()):
            if len(pairs) >= ns.ece_min_per_tag:
                ed = _binary_ece_equal_width(pairs, ns.ece_bins)
                if ed:
                    by_tag_ece[tag] = ed
        if by_tag_ece:
            metrics["ece_binary_by_domain_tag"] = by_tag_ece
    min_psy = max(1, int(ns.psy_state_min_per_band))
    band_doc: dict[str, Any] = {}
    if len(brier_by_psy_low) >= min_psy:
        band_doc["psychological_state_term_le_0.5"] = {
            "mean_brier_score": round(sum(brier_by_psy_low) / len(brier_by_psy_low), 6),
            "n_evaluated": len(brier_by_psy_low),
        }
    if len(brier_by_psy_high) >= min_psy:
        band_doc["psychological_state_term_gt_0.5"] = {
            "mean_brier_score": round(sum(brier_by_psy_high) / len(brier_by_psy_high), 6),
            "n_evaluated": len(brier_by_psy_high),
        }
    if band_doc:
        band_doc["split_threshold"] = 0.5
        band_doc["min_per_band"] = min_psy
        metrics["by_psychological_state_term_band"] = band_doc
    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "inputs": {"registry_path": str(ns.input.resolve())},
        "metrics": metrics,
        "note": "binary + resolved + last forecast only; void/categorical skipped; missing prophecy_track -> general; optional auxiliary_covariates_v1.psychological_state_term -> metrics.by_psychological_state_term_band when per-band n>=min",
    }
    if not ns.no_rows:
        out["rows"] = rows
    text = json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    if ns.stdout_only:
        sys.stdout.write(text)
        return 0
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(text, encoding="utf-8")
    if not ns.no_print_output_path:
        print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
