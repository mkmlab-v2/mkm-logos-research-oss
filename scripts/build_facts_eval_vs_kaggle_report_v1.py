#!/usr/bin/env python3
"""Merge internal FACTS-style eval (facts_minimal_eval_v1) with Kaggle leaderboard snapshot.

Internal metrics (answered_acc, hold_rate, etc.) and Kaggle public leaderboard scores
are not directly comparable without identical prompts, tools, and judge; the report
makes that explicit in `comparison_note`.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def _find_kaggle_model(
    models: list[dict[str, Any]],
    *,
    display_name: str | None,
    slug: str | None,
    model_proxy_slug: str | None,
    model_version_id: int | None,
) -> dict[str, Any] | None:
    if model_version_id is not None:
        for m in models:
            if m.get("model_version_id") == model_version_id:
                return m
    if slug:
        s = _norm(slug)
        for m in models:
            if m.get("slug") and _norm(str(m["slug"])) == s:
                return m
    if model_proxy_slug:
        s = _norm(model_proxy_slug)
        for m in models:
            if m.get("model_proxy_slug") and _norm(str(m["model_proxy_slug"])) == s:
                return m
    if display_name:
        s = _norm(display_name)
        for m in models:
            dn = m.get("display_name")
            if isinstance(dn, str) and _norm(dn) == s:
                return m
    return None


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build combined internal eval + Kaggle FACTS snapshot report."
    )
    p.add_argument(
        "--internal-eval-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_minimal_eval_latest.json"),
    )
    p.add_argument(
        "--kaggle-leaderboard-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_kaggle_leaderboard_latest.json"),
    )
    p.add_argument(
        "--out-json",
        type=Path,
        default=Path("docs/final/artifacts/facts_eval_vs_kaggle_report_latest.json"),
    )
    p.add_argument(
        "--model-display-name",
        default=None,
        help="Match Kaggle row by displayName (case-insensitive).",
    )
    p.add_argument("--model-slug", default=None, help="Match Kaggle row by model slug.")
    p.add_argument(
        "--model-proxy-slug",
        default=None,
        help="Match Kaggle row by modelProxySlug (e.g. openai/gpt-5.5-2026-04-23).",
    )
    p.add_argument(
        "--model-version-id",
        type=int,
        default=None,
        help="Match Kaggle row by model_version_id.",
    )
    p.add_argument(
        "--top-kaggle-models",
        type=int,
        default=10,
        help="Include top N models from Kaggle snapshot (by rank). Use 0 for none.",
    )
    return p


def main() -> int:
    args = build_arg_parser().parse_args()

    if not args.internal_eval_json.is_file():
        print(f"[ERROR] missing internal eval: {args.internal_eval_json}", file=sys.stderr)
        return 2
    if not args.kaggle_leaderboard_json.is_file():
        print(f"[ERROR] missing Kaggle snapshot: {args.kaggle_leaderboard_json}", file=sys.stderr)
        return 2

    internal_raw = json.loads(args.internal_eval_json.read_text(encoding="utf-8"))
    kaggle_raw = json.loads(args.kaggle_leaderboard_json.read_text(encoding="utf-8"))

    if internal_raw.get("schema") != "facts_minimal_eval_v1":
        print("[WARN] internal eval schema is not facts_minimal_eval_v1", file=sys.stderr)
    if kaggle_raw.get("schema") != "facts_kaggle_leaderboard_snapshot_v1":
        print("[WARN] Kaggle snapshot schema is not facts_kaggle_leaderboard_snapshot_v1", file=sys.stderr)

    kaggle_models = kaggle_raw.get("models") or []
    matched = _find_kaggle_model(
        kaggle_models,
        display_name=args.model_display_name,
        slug=args.model_slug,
        model_proxy_slug=args.model_proxy_slug,
        model_version_id=args.model_version_id,
    )

    top_slice: list[dict[str, Any]] = []
    if args.top_kaggle_models and args.top_kaggle_models > 0:
        top_slice = kaggle_models[: args.top_kaggle_models]

    report = {
        "schema": "facts_eval_vs_kaggle_report_v1",
        "generated_at_utc": _now_utc_iso(),
        "comparison_note": (
            "Internal metrics (facts_minimal_eval_v1) measure HOLD-aware behavior on a "
            "local protocol; Kaggle scores are from the public FACTS leaderboard API snapshot. "
            "Direct numeric equivalence requires identical suite subset, prompts, tools, and scoring."
        ),
        "inputs": {
            "internal_eval_json": str(args.internal_eval_json),
            "internal_eval_sha256": _sha256_file(args.internal_eval_json),
            "kaggle_leaderboard_json": str(args.kaggle_leaderboard_json),
            "kaggle_leaderboard_sha256": _sha256_file(args.kaggle_leaderboard_json),
            "match": {
                "model_display_name": args.model_display_name,
                "model_slug": args.model_slug,
                "model_proxy_slug": args.model_proxy_slug,
                "model_version_id": args.model_version_id,
                "matched": matched is not None,
            },
        },
        "internal_eval": {
            "generated_at_utc": internal_raw.get("generated_at_utc"),
            "metrics": internal_raw.get("metrics"),
            "inputs_summary": {
                k: internal_raw.get("inputs", {}).get(k)
                for k in (
                    "preset",
                    "id_field",
                    "answer_field",
                    "prediction_field",
                    "decision_field",
                    "unknown_field",
                )
                if isinstance(internal_raw.get("inputs"), dict)
            },
        },
        "kaggle_snapshot": {
            "generated_at_utc": kaggle_raw.get("generated_at_utc"),
            "source": kaggle_raw.get("source"),
            "summary": kaggle_raw.get("summary"),
            "tasks": kaggle_raw.get("tasks"),
        },
        "kaggle_top_models": top_slice,
        "side_by_side": None,
    }

    if matched:
        avg = (matched.get("scores") or {}).get("Average") or {}
        report["side_by_side"] = {
            "kaggle_model": {
                "rank": matched.get("rank"),
                "display_name": matched.get("display_name"),
                "slug": matched.get("slug"),
                "model_proxy_slug": matched.get("model_proxy_slug"),
                "model_version_id": matched.get("model_version_id"),
                "kaggle_average_score": avg.get("score"),
                "kaggle_average_ci": avg.get("confidence_interval"),
                "kaggle_scores_by_pillar": matched.get("scores"),
            },
            "internal_metrics": internal_raw.get("metrics"),
        }

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] wrote: {args.out_json}")
    if matched:
        print(f"[MATCH] Kaggle model: {matched.get('display_name')} (rank {matched.get('rank')})")
    else:
        print("[MATCH] none — side_by_side null (pass --model-display-name or --model-slug etc.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
