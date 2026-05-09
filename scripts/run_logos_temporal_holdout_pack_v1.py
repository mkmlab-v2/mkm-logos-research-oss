#!/usr/bin/env python3
"""Build temporal holdout bins and evaluate backtest/fractal on each bin."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from collections import defaultdict

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"

NEWS_LATEST = ART / "news_observation_v1_latest.jsonl"
NEWS_NON_SYNTH_BALANCED = ART / "news_observation_v1_non_synthetic_date_balanced_latest.jsonl"
LABEL_LATEST = ART / "direction_label_bar_v1_latest.jsonl"
SYMBOL_MAP = ART / "logos_symbolic_event_map_v1.json"
BASE_MATRIX = ART / "logos_fractal_archetype_4d_matrix_v1.json"
CAND_MATRIX = ART / "logos_fractal_archetype_4d_matrix_refit_candidate_v1.json"

OUT_SUMMARY = ART / "logos_temporal_holdout_pack_latest.json"


def _parse_dt(v: str) -> datetime:
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(timezone.utc)


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw:
            continue
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            rows.append(obj)
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n{cp.stdout}\n{cp.stderr}")


def _load_json(path: Path) -> dict[str, Any]:
    last_err: Exception | None = None
    for _ in range(5):
        try:
            raw = path.read_text(encoding="utf-8")
            if raw.strip():
                return json.loads(raw)
        except Exception as exc:  # noqa: BLE001
            last_err = exc
        time.sleep(0.05)
    if last_err is not None:
        raise last_err
    raise RuntimeError(f"Failed to load non-empty JSON from {path}")


def _weighted_cosine(a: dict[str, float], b: dict[str, float], w: dict[str, float]) -> float:
    import math

    dims = ("S", "L", "K", "M")
    dot = sum(w[d] * a[d] * b[d] for d in dims)
    na = math.sqrt(sum(w[d] * a[d] * a[d] for d in dims))
    nb = math.sqrt(sum(w[d] * b[d] * b[d] for d in dims))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _best_resonance(current: dict[str, float], matrix_json: Path, weights: dict[str, float]) -> tuple[str, float]:
    m = _load_json(matrix_json)
    best_id = "unknown"
    best = -1.0
    for a in m.get("archetypes", []):
        v = a.get("vector_slkm") or {}
        vec = {
            "S": float(v.get("S", 0.5)),
            "L": float(v.get("L", 0.5)),
            "K": float(v.get("K", 0.5)),
            "M": float(v.get("M", 0.5)),
        }
        r = _weighted_cosine(current, vec, weights)
        if r > best:
            best = r
            best_id = str(a.get("id", "unknown"))
    return best_id, round(best, 6)


def main() -> int:
    ap = argparse.ArgumentParser(description="Temporal holdout pack for Logos fractal evaluation.")
    ap.add_argument("--bins", type=int, default=6)
    ap.add_argument("--min-non-synth-per-bin", type=int, default=10)
    ap.add_argument("--group-by-date", action="store_true")
    ap.add_argument("--use-non-synthetic-date-balanced", action="store_true")
    ap.add_argument("--output-json", type=Path, default=OUT_SUMMARY)
    args = ap.parse_args()

    news_source_path = NEWS_NON_SYNTH_BALANCED if args.use_non_synthetic_date_balanced else NEWS_LATEST
    news = _load_jsonl(news_source_path)
    news = [r for r in news if r.get("as_of_utc")]
    news.sort(key=lambda r: _parse_dt(str(r["as_of_utc"])))
    n = len(news)
    if n == 0:
        raise RuntimeError("No news rows in latest set.")

    bins = max(2, int(args.bins))
    min_non_synth = max(1, int(args.min_non_synth_per_bin))
    weights = {"S": 0.994, "L": 0.508, "K": 0.957, "M": 1.48}
    synthetic_ids = {"label_guided_seed", "manual_seed"}

    def _build_row_slices() -> list[list[dict[str, Any]]]:
        out: list[list[dict[str, Any]]] = []
        cur_local: list[dict[str, Any]] = []
        cur_ns_local = 0
        for rw in news:
            cur_local.append(rw)
            if str(rw.get("source_id", "")) not in synthetic_ids:
                cur_ns_local += 1
            if cur_ns_local >= min_non_synth and len(out) < bins - 1:
                out.append(cur_local)
                cur_local = []
                cur_ns_local = 0
        if cur_local:
            out.append(cur_local)
        return out

    # Build bins by enforcing minimum non-synthetic count per bin.
    # Optionally aggregate by unique as_of date first to avoid timestamp clustering.
    slices: list[list[dict[str, Any]]] = []
    binning_mode_used = "row_sequential"
    if args.group_by_date:
        by_day: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in news:
            day = str(row.get("as_of_utc", ""))[:10]
            by_day[day].append(row)
        ordered_days = sorted(by_day.keys())
        cur: list[dict[str, Any]] = []
        cur_ns = 0
        for day in ordered_days:
            day_rows = by_day[day]
            cur.extend(day_rows)
            cur_ns += sum(1 for r in day_rows if str(r.get("source_id", "")) not in synthetic_ids)
            if cur_ns >= min_non_synth and len(slices) < bins - 1:
                slices.append(cur)
                cur = []
                cur_ns = 0
        if cur:
            slices.append(cur)
        binning_mode_used = "as_of_date"
        # Fallback: if unique-date grouping collapses into one bin, revert to row mode.
        if len(slices) < 2 and bins > 1:
            slices = _build_row_slices()
            binning_mode_used = "as_of_date_fallback_row"
    else:
        slices = _build_row_slices()
    if not slices:
        slices = [news]

    runs: list[dict[str, Any]] = []
    for i, slice_rows in enumerate(slices):
        if not slice_rows:
            continue
        tag = f"temporal_bin{i+1:02d}"
        news_path = ART / f"news_observation_v1_{tag}_latest.jsonl"
        bt_path = ART / f"logos_symbolic_event_backtest_{tag}_latest.json"
        bt_csv = ART / f"logos_symbolic_event_backtest_{tag}_rows_latest.csv"
        frac_path = ART / f"logos_fractal_sign_reading_{tag}_latest.json"
        _write_jsonl(news_path, slice_rows)

        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_logos_symbolic_event_backtest_v1.py"),
                "--news-jsonl",
                str(news_path),
                "--labels-jsonl",
                str(LABEL_LATEST),
                "--symbol-map-json",
                str(SYMBOL_MAP),
                "--output-json",
                str(bt_path),
                "--output-csv",
                str(bt_csv),
            ]
        )
        _run(
            [
                sys.executable,
                str(ROOT / "scripts" / "run_logos_fractal_sign_reading_v1.py"),
                "--news-jsonl",
                str(news_path),
                "--matrix-json",
                str(BASE_MATRIX),
                "--output-json",
                str(frac_path),
            ]
        )

        bt = _load_json(bt_path)
        frac = _load_json(frac_path)
        current = frac.get("current_vector_slkm") or {"S": 0.5, "L": 0.5, "K": 0.5, "M": 0.5}
        base_top = frac.get("top_match") or {}
        cand_id, cand_res = _best_resonance(
            {k: float(current.get(k, 0.5)) for k in ("S", "L", "K", "M")},
            CAND_MATRIX,
            weights,
        )
        summ = bt.get("summary") or {}
        runs.append(
            {
                "tag": tag,
                "news_row_count": len(slice_rows),
                "news_non_synthetic_row_count": sum(
                    1 for r in slice_rows if str(r.get("source_id", "")) not in synthetic_ids
                ),
                "window": {"start_as_of_utc": slice_rows[0]["as_of_utc"], "end_as_of_utc": slice_rows[-1]["as_of_utc"]},
                "hit_rate": float(summ.get("hit_rate") or 0.0),
                "non_synthetic_n_evaluated": int(summ.get("non_synthetic_n_evaluated") or 0),
                "non_synthetic_hit_rate": float(summ.get("non_synthetic_hit_rate") or 0.0),
                "base_top_archetype": base_top.get("archetype_id"),
                "base_resonance_cosine": float(base_top.get("resonance_cosine") or 0.0),
                "candidate_top_archetype": cand_id,
                "candidate_resonance_cosine": cand_res,
            }
        )

    # Correlation summary
    def _corr(xs: list[float], ys: list[float]) -> float | None:
        import math
        from statistics import mean

        if len(xs) < 2 or len(xs) != len(ys):
            return None
        mx, my = mean(xs), mean(ys)
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        denx = math.sqrt(sum((x - mx) ** 2 for x in xs))
        deny = math.sqrt(sum((y - my) ** 2 for y in ys))
        if denx == 0.0 or deny == 0.0:
            return None
        return round(num / (denx * deny), 6)

    x_base = [float(r["base_resonance_cosine"]) for r in runs]
    x_cand = [float(r["candidate_resonance_cosine"]) for r in runs]
    y_ns = [float(r["non_synthetic_hit_rate"]) for r in runs]
    eligible_ns = [r for r in runs if int(r.get("non_synthetic_n_evaluated", 0)) > 0]
    x_base_ns = [float(r["base_resonance_cosine"]) for r in eligible_ns]
    x_cand_ns = [float(r["candidate_resonance_cosine"]) for r in eligible_ns]
    y_ns_eligible = [float(r["non_synthetic_hit_rate"]) for r in eligible_ns]

    out = {
        "schema": "logos_temporal_holdout_pack_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "source_track": "B",
        "research_only": True,
        "auto_bind_to_atrack_forbidden": True,
        "bins_requested": bins,
        "min_non_synth_per_bin_requested": min_non_synth,
        "group_by_date": bool(args.group_by_date),
        "use_non_synthetic_date_balanced": bool(args.use_non_synthetic_date_balanced),
        "news_source_path": str(news_source_path).replace("\\", "/"),
        "binning_mode_used": binning_mode_used,
        "bins_built": len(runs),
        "runs": runs,
        "summary": {
            "corr_base_resonance_vs_non_synthetic_hit_rate": _corr(x_base, y_ns),
            "corr_candidate_resonance_vs_non_synthetic_hit_rate": _corr(x_cand, y_ns),
            "eligible_non_synthetic_bin_count": len(eligible_ns),
            "corr_base_resonance_vs_non_synthetic_hit_rate_eligible_only": _corr(x_base_ns, y_ns_eligible),
            "corr_candidate_resonance_vs_non_synthetic_hit_rate_eligible_only": _corr(x_cand_ns, y_ns_eligible),
        },
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output_json": str(args.output_json), "bins_built": len(runs), "summary": out["summary"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

