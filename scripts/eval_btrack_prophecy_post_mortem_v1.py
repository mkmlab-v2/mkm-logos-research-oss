#!/usr/bin/env python3
"""B-Track post-mortem: join hypothesis + score (+ optional hit-rate eval) into one report.

Does not re-read OHLCV CSVs; uses ``btrack_prophecy_score_v1`` rows as truth for direction.
Uses ``runtime_meta.lens_values`` on the hypothesis when present; otherwise emits warnings only.

Output schema: ``btrack_post_mortem_v1`` → ``docs/final/artifacts/btrack_post_mortem_latest.json`` (default).
Research / [HYPO] only — not a live trading trigger.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent

DEFAULT_HYPOTHESIS = ROOT / "docs" / "final" / "artifacts" / "btrack_hypothesis_prophecy_latest.json"
DEFAULT_SCORE = ROOT / "docs" / "final" / "artifacts" / "btrack_prophecy_score_latest.json"
DEFAULT_HIT_RATE = ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_eval_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "btrack_post_mortem_latest.json"

SCHEMA = "btrack_post_mortem_v1"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _norm_path(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(p.resolve()).replace("\\", "/")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _score_to_direction(score: float) -> str:
    if score > 1e-12:
        return "bull"
    if score < -1e-12:
        return "bear"
    return "neutral"


def _normalize_dir(v: Any) -> str | None:
    d = str(v or "").strip().lower()
    if d in ("bull", "bear", "neutral"):
        return d
    return None


def build_post_mortem(
    *,
    hypothesis: dict[str, Any],
    score: dict[str, Any],
    hit_rate: dict[str, Any] | None,
    hypothesis_path: Path,
    score_path: Path,
    hit_rate_path: Path | None,
) -> dict[str, Any]:
    warnings: list[str] = []
    runtime = hypothesis.get("runtime_meta") or {}
    lens_values = runtime.get("lens_values") if isinstance(runtime.get("lens_values"), dict) else {}
    if not lens_values:
        warnings.append("hypothesis_missing_runtime_meta_lens_values")

    rows_raw = score.get("rows")
    rows: list[dict[str, Any]] = [r for r in rows_raw if isinstance(r, dict)] if isinstance(rows_raw, list) else []

    hyp_path_in_score = score.get("hypothesis_path")
    if hyp_path_in_score and str(hyp_path_in_score).replace("\\", "/") != _norm_path(hypothesis_path):
        warnings.append("score_hypothesis_path_mismatch_with_cli_input")

    lens_ids = sorted(lens_values.keys()) if lens_values else []
    per_row: list[dict[str, Any]] = []
    lens_totals: dict[str, dict[str, int]] = {lid: {"n": 0, "hits": 0} for lid in lens_ids}

    for r in rows:
        inst = str(r.get("instrument") or "").lower()
        eval_date = str(r.get("eval_date") or score.get("eval_date") or "")
        pred = _normalize_dir(r.get("predicted_direction"))
        actual = _normalize_dir(r.get("actual_direction"))
        row_out: dict[str, Any] = {
            "instrument": inst,
            "eval_date": eval_date,
            "predicted_direction": pred,
            "actual_direction": actual,
            "lenses": {},
        }
        if not pred or not actual:
            row_out["skip_reason"] = "missing_predicted_or_actual"
            per_row.append(row_out)
            continue

        for lid in lens_ids:
            lv = lens_values.get(lid)
            if not isinstance(lv, dict):
                continue
            try:
                sc = float(lv.get("score", 0.0) or 0.0)
            except (TypeError, ValueError):
                sc = 0.0
            conf = lv.get("confidence")
            implied = _score_to_direction(sc)
            hit = implied == actual
            row_out["lenses"][lid] = {
                "score": sc,
                "confidence": conf,
                "implied_direction": implied,
                "match_actual": hit,
            }
            lens_totals[lid]["n"] += 1
            if hit:
                lens_totals[lid]["hits"] += 1
        per_row.append(row_out)

    lens_accuracy: dict[str, Any] = {}
    for lid, tot in lens_totals.items():
        n, h = tot["n"], tot["hits"]
        lens_accuracy[lid] = {
            "n_evaluated": n,
            "hits": h,
            "hit_rate": round(h / n, 6) if n else None,
        }

    hit_summary: dict[str, Any] | None = None
    if hit_rate:
        hit_summary = {
            "schema": hit_rate.get("schema"),
            "status": hit_rate.get("status"),
            "run_mode": hit_rate.get("run_mode"),
            "metrics": hit_rate.get("metrics"),
            "path": _norm_path(hit_rate_path) if hit_rate_path else None,
        }

    out: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "inputs": {
            "hypothesis_json": _norm_path(hypothesis_path),
            "score_json": _norm_path(score_path),
            "hit_rate_eval_json": _norm_path(hit_rate_path) if hit_rate_path and hit_rate_path.is_file() else None,
        },
        "score_meta": {
            "eval_date": score.get("eval_date"),
            "schema": score.get("schema"),
            "row_count": len(rows),
        },
        "hypothesis_meta": {
            "ts_utc": hypothesis.get("ts_utc"),
            "label": hypothesis.get("label"),
            "prediction": hypothesis.get("prediction"),
        },
        "hit_rate_eval_summary": hit_summary,
        "lens_ids": lens_ids,
        "lens_accuracy": lens_accuracy,
        "rows": per_row,
        "warnings": warnings,
    }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="B-Track post-mortem (hypothesis + score + optional eval).")
    ap.add_argument("--hypothesis-json", type=Path, default=DEFAULT_HYPOTHESIS)
    ap.add_argument("--score-json", type=Path, default=DEFAULT_SCORE)
    ap.add_argument(
        "--hit-rate-json",
        type=Path,
        default=DEFAULT_HIT_RATE,
        help="Optional; pass a non-existent path to skip (e.g. NUL on Windows — use --no-hit-rate).",
    )
    ap.add_argument("--no-hit-rate", action="store_true", help="Do not load hit-rate eval JSON.")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    hyp = _load_json(args.hypothesis_json)
    if not hyp:
        print(f"missing_or_invalid_hypothesis: {args.hypothesis_json}", file=sys.stderr)
        return 1
    sc = _load_json(args.score_json)
    if not sc:
        print(f"missing_or_invalid_score: {args.score_json}", file=sys.stderr)
        return 1

    hr_path: Path | None = None if args.no_hit_rate else args.hit_rate_json
    hr: dict[str, Any] | None = None
    if hr_path and hr_path.is_file():
        hr = _load_json(hr_path)
        if not hr:
            print(f"invalid_hit_rate_json: {hr_path}", file=sys.stderr)
            return 1

    payload = build_post_mortem(
        hypothesis=hyp,
        score=sc,
        hit_rate=hr,
        hypothesis_path=args.hypothesis_json,
        score_path=args.score_json,
        hit_rate_path=hr_path if hr_path and hr_path.is_file() else None,
    )
    if not args.no_hit_rate and hr_path and not hr_path.is_file():
        payload.setdefault("warnings", []).append("hit_rate_path_missing")

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
