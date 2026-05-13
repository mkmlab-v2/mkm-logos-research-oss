#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pearson/Spearman correlations for numeric columns in a joined wide CSV (B-track, [HYPO]).

**Pipeline order:** panel → (optional weather + OHLCV) → ``join_btrack_session_panel_weather_ohlcv_v1.py``
→ **this script** → JSON summary. No HTTP. Not a trading trigger.

SciPy optional: when available, fills ``p_value_pearson`` / ``p_value_spearman`` (two-sided).
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_OUT = ROOT / "reports" / "btrack_joined_wide_correlation_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    text = path.read_text(encoding="utf-8-sig")
    lines = text.splitlines()
    if not lines:
        return [], []
    r = csv.DictReader(lines)
    h = list(r.fieldnames or [])
    rows = [{k: (v if v is not None else "") for k, v in row.items()} for row in r]
    return h, rows


def _rankdata(a: list[float]) -> list[float]:
    indexed = sorted(enumerate(a), key=lambda x: x[1])
    ranks = [0.0] * len(a)
    i = 0
    n = len(a)
    while i < n:
        j = i
        val = indexed[i][1]
        while j < n and indexed[j][1] == val:
            j += 1
        avg_rank = (i + j + 1) / 2.0
        for k in range(i, j):
            orig_idx = indexed[k][0]
            ranks[orig_idx] = avg_rank
        i = j
    return ranks


def _pearson_r(xs: list[float], ys: list[float]) -> float:
    n = len(xs)
    if n < 2:
        return float("nan")
    mx = sum(xs) / n
    my = sum(ys) / n
    num = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
    deny = math.sqrt(sum((y - my) ** 2 for y in ys))
    if denx <= 0.0 or deny <= 0.0:
        return float("nan")
    return num / (denx * deny)


def _spearman_r(xs: list[float], ys: list[float]) -> float:
    return _pearson_r(_rankdata(xs), _rankdata(ys))


def _try_scipy_pvalues(
    xs: list[float], ys: list[float]
) -> tuple[float | None, float | None, float | None, float | None]:
    try:
        from scipy.stats import pearsonr, spearmanr

        pr = pearsonr(xs, ys)
        sr = spearmanr(xs, ys)
        pr_r = float(pr.statistic) if hasattr(pr, "statistic") else float(pr[0])
        pr_p = float(pr.pvalue) if hasattr(pr, "pvalue") else float(pr[1])
        sr_r = float(sr.statistic) if hasattr(sr, "statistic") else float(sr[0])
        sr_p = float(sr.pvalue) if hasattr(sr, "pvalue") else float(sr[1])
        return pr_r, pr_p, sr_r, sr_p
    except Exception:
        return None, None, None, None


def _expand_x_from_prefixes(headers: list[str], y_col: str, prefixes_csv: str) -> list[str]:
    prefs = [p.strip() for p in prefixes_csv.split(",") if p.strip()]
    if not prefs:
        return []
    out: list[str] = []
    for h in headers:
        if not h or h == y_col:
            continue
        if any(h.startswith(p) for p in prefs):
            out.append(h)
    return out


def _aligned_pairs(
    rows: list[dict[str, str]], x_col: str, y_col: str
) -> tuple[list[float], list[float]]:
    xs: list[float] = []
    ys: list[float] = []
    for r in rows:
        if x_col not in r or y_col not in r:
            continue
        try:
            xv = float(str(r[x_col]).strip())
            yv = float(str(r[y_col]).strip())
        except ValueError:
            continue
        if math.isfinite(xv) and math.isfinite(yv):
            xs.append(xv)
            ys.append(yv)
    return xs, ys


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input-csv", type=Path, required=True, help="Wide CSV from join_btrack_session_panel_weather_ohlcv_v1.py")
    ap.add_argument("--y-col", type=str, required=True)
    ap.add_argument(
        "--x-cols",
        type=str,
        default=None,
        help="Comma-separated predictor columns (exact header names). Mutually exclusive with --x-auto-prefixes.",
    )
    ap.add_argument(
        "--x-auto-prefixes",
        type=str,
        default=None,
        metavar="PREFIXES",
        help="Comma-separated prefixes (e.g. elem_,wthr_,ohlcv_): use every header column matching any prefix, "
        "excluding --y-col, in CSV column order.",
    )
    ap.add_argument("--min-pairs", type=int, default=3, metavar="N", help="Skip x if fewer than N aligned finite pairs.")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ns = ap.parse_args()

    if not ns.input_csv.is_file():
        print(f"missing {ns.input_csv}", file=sys.stderr)
        return 2
    headers, rows = _read_csv(ns.input_csv)
    if not headers or not rows:
        print("empty csv", file=sys.stderr)
        return 2
    y_col = ns.y_col.strip()
    if y_col not in headers:
        print(f"y-col not in header: {y_col}", file=sys.stderr)
        return 2

    if bool(ns.x_cols) == bool(ns.x_auto_prefixes):
        print("require exactly one of --x-cols or --x-auto-prefixes", file=sys.stderr)
        return 2
    if ns.x_auto_prefixes:
        x_cols = _expand_x_from_prefixes(headers, y_col, ns.x_auto_prefixes)
        if not x_cols:
            print("x-auto-prefixes matched no columns", file=sys.stderr)
            return 2
    else:
        x_cols = [c.strip() for c in (ns.x_cols or "").split(",") if c.strip()]
        if not x_cols:
            print("no x-cols", file=sys.stderr)
            return 2
        for xc in x_cols:
            if xc not in headers:
                print(f"x-col not in header: {xc}", file=sys.stderr)
                return 2

    min_n = max(2, int(ns.min_pairs))
    correlations: list[dict[str, Any]] = []
    for xc in x_cols:
        xs, ys = _aligned_pairs(rows, xc, y_col)
        n = len(xs)
        if n < min_n:
            correlations.append(
                {
                    "x_col": xc,
                    "y_col": y_col,
                    "status": "skipped",
                    "n_pairs": n,
                    "skipped_reason": f"need_at_least_{min_n}_pairs",
                    "pearson_r": None,
                    "spearman_r": None,
                    "p_value_pearson": None,
                    "p_value_spearman": None,
                }
            )
            continue
        pr = _pearson_r(xs, ys)
        sr = _spearman_r(xs, ys)
        pr_p, sr_p = None, None
        spr = _try_scipy_pvalues(xs, ys)
        if spr[1] is not None:
            pr_p = spr[1]
        if spr[3] is not None:
            sr_p = spr[3]
        correlations.append(
            {
                "x_col": xc,
                "y_col": y_col,
                "status": "computed",
                "n_pairs": n,
                "skipped_reason": None,
                "pearson_r": pr if pr == pr else None,
                "spearman_r": sr if sr == sr else None,
                "p_value_pearson": pr_p,
                "p_value_spearman": sr_p,
            }
        )

    out_doc: dict[str, Any] = {
        "schema": "btrack_joined_wide_correlation_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "boundary_ack": True,
        "inputs": {"csv_path": str(ns.input_csv.resolve())},
        "params": {
            "y_col": y_col,
            "x_cols": x_cols,
            "x_auto_prefixes": ns.x_auto_prefixes,
            "min_pairs": min_n,
        },
        "n_csv_rows": len(rows),
        "correlations": correlations,
        "note_ko": "탐색용 상관 요약이다. 다중비교·인과 단정 금지. Track A·실매매 자동 합선 없음.",
    }

    text = json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n"
    if ns.stdout_only:
        sys.stdout.write(text)
        return 0
    ns.out_json.parent.mkdir(parents=True, exist_ok=True)
    ns.out_json.write_text(text, encoding="utf-8")
    print(str(ns.out_json.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
