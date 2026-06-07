#!/usr/bin/env python3
"""A/B compare biblical resonance eval: production vs research slice (+ optional DSS merge)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROD_NEWS = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_SLICE = ROOT / "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_latest.jsonl"
DEFAULT_DSS = ROOT / "docs/final/artifacts/news_observation_v1_dss_apocrypha_research_context_latest.jsonl"
DEFAULT_NDJSON = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_research_context_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/biblical_resonance_research_production_ab_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            obj = json.loads(line)
            if isinstance(obj, dict):
                rows.append(obj)
    return rows


def _row_key(row: dict[str, Any]) -> str:
    return str(row.get("text_sha256") or row.get("observation_id") or "")


def _merge_jsonl(paths: list[Path], out_path: Path) -> int:
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    for path in paths:
        for row in _load_jsonl(path):
            key = _row_key(row)
            if not key or key in seen:
                continue
            seen.add(key)
            merged.append(row)
    merged.sort(key=lambda r: str(r.get("as_of_utc") or ""))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + ("\n" if merged else ""),
        encoding="utf-8",
    )
    return len(merged)


def _run_eval(news_jsonl: Path, out_json: Path, lookback_days: int) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/evaluate_biblical_resonance_hypotheses_v1.py"),
        "--news-jsonl",
        str(news_jsonl),
        "--lookback-days",
        str(lookback_days),
        "--output-json",
        str(out_json),
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), check=False, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or f"eval failed: {news_jsonl}")
    return _load_json(out_json)


def _hyp_row(doc: dict[str, Any], hyp_id: str) -> dict[str, Any] | None:
    for row in doc.get("hypotheses") or []:
        if isinstance(row, dict) and row.get("id") == hyp_id:
            return row
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--production-news-jsonl", type=Path, default=DEFAULT_PROD_NEWS)
    ap.add_argument("--research-slice-jsonl", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--dss-context-jsonl", type=Path, default=DEFAULT_DSS)
    ap.add_argument("--ndjson-context-jsonl", type=Path, default=DEFAULT_NDJSON)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--hypothesis-id", default="H-DSS1")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-prod-plus-dss", action="store_true")
    args = ap.parse_args()

    tmp_dir = Path(tempfile.mkdtemp(prefix="biblical_res_ab_"))
    prod_eval_path = tmp_dir / "prod_eval.json"
    slice_eval_path = tmp_dir / "slice_eval.json"
    merged_eval_path = tmp_dir / "prod_plus_dss_eval.json"
    merged_news = tmp_dir / "prod_plus_dss_news.jsonl"
    slice_ndjson_news = tmp_dir / "slice_plus_ndjson_news.jsonl"
    slice_ndjson_eval_path = tmp_dir / "slice_plus_ndjson_eval.json"
    prod_ndjson_news = tmp_dir / "prod_plus_ndjson_news.jsonl"
    prod_ndjson_eval_path = tmp_dir / "prod_plus_ndjson_eval.json"

    prod_eval = _run_eval(args.production_news_jsonl, prod_eval_path, args.lookback_days)
    slice_eval = _run_eval(args.research_slice_jsonl, slice_eval_path, args.lookback_days)

    prod_plus_dss_eval: dict[str, Any] | None = None
    merged_row_count = 0
    if not args.skip_prod_plus_dss and args.dss_context_jsonl.is_file():
        merged_row_count = _merge_jsonl([args.production_news_jsonl, args.dss_context_jsonl], merged_news)
        prod_plus_dss_eval = _run_eval(merged_news, merged_eval_path, args.lookback_days)

    slice_plus_ndjson_eval: dict[str, Any] | None = None
    slice_ndjson_row_count = 0
    if args.ndjson_context_jsonl.is_file():
        slice_ndjson_row_count = _merge_jsonl(
            [args.research_slice_jsonl, args.ndjson_context_jsonl], slice_ndjson_news
        )
        slice_plus_ndjson_eval = _run_eval(slice_ndjson_news, slice_ndjson_eval_path, args.lookback_days)

    prod_plus_ndjson_eval: dict[str, Any] | None = None
    prod_ndjson_row_count = 0
    if args.ndjson_context_jsonl.is_file():
        prod_ndjson_row_count = _merge_jsonl(
            [args.production_news_jsonl, args.ndjson_context_jsonl], prod_ndjson_news
        )
        prod_plus_ndjson_eval = _run_eval(prod_ndjson_news, prod_ndjson_eval_path, args.lookback_days)

    hyp_id = args.hypothesis_id
    prod_h = _hyp_row(prod_eval, hyp_id) or {}
    slice_h = _hyp_row(slice_eval, hyp_id) or {}
    merged_h = _hyp_row(prod_plus_dss_eval, hyp_id) if prod_plus_dss_eval else None
    slice_ndjson_h = _hyp_row(slice_plus_ndjson_eval, hyp_id) if slice_plus_ndjson_eval else None
    prod_ndjson_h = _hyp_row(prod_plus_ndjson_eval, hyp_id) if prod_plus_ndjson_eval else None

    def _delta(a: dict[str, Any], b: dict[str, Any], key: str) -> float | None:
        av = a.get(key)
        bv = b.get(key)
        if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
            return round(float(bv) - float(av), 6)
        return None

    payload = {
        "schema": "biblical_resonance_research_production_ab_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "hypothesis_id": hyp_id,
        "window_days": args.lookback_days,
        "arms": {
            "production": {
                "news_jsonl": str(args.production_news_jsonl),
                "news_row_count": prod_eval.get("inputs", {}).get("news_row_count"),
                "hypothesis": prod_h,
            },
            "research_slice": {
                "news_jsonl": str(args.research_slice_jsonl),
                "news_row_count": slice_eval.get("inputs", {}).get("news_row_count"),
                "hypothesis": slice_h,
            },
        },
        "delta_research_slice_minus_production": {
            "matched_rows": _delta(prod_h, slice_h, "matched_rows"),
            "coverage_ratio": _delta(prod_h, slice_h, "coverage_ratio"),
            "composite_score": _delta(prod_h, slice_h, "composite_score"),
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": "Slice is controlled research corpus; production is live news ledger. Delta is observational only.",
        },
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }

    if merged_h is not None:
        payload["arms"]["production_plus_dss_context"] = {
            "news_jsonl": str(merged_news),
            "merged_row_count": merged_row_count,
            "news_row_count": prod_plus_dss_eval.get("inputs", {}).get("news_row_count") if prod_plus_dss_eval else None,
            "hypothesis": merged_h,
        }
        payload["delta_prod_plus_dss_minus_production"] = {
            "matched_rows": _delta(prod_h, merged_h, "matched_rows"),
            "coverage_ratio": _delta(prod_h, merged_h, "coverage_ratio"),
            "composite_score": _delta(prod_h, merged_h, "composite_score"),
        }

    if slice_ndjson_h is not None:
        payload["arms"]["research_slice_plus_ndjson_context"] = {
            "news_jsonl": str(slice_ndjson_news),
            "merged_row_count": slice_ndjson_row_count,
            "ndjson_context_jsonl": str(args.ndjson_context_jsonl),
            "news_row_count": slice_plus_ndjson_eval.get("inputs", {}).get("news_row_count")
            if slice_plus_ndjson_eval
            else None,
            "hypothesis": slice_ndjson_h,
        }
        payload["delta_slice_plus_ndjson_minus_research_slice"] = {
            "matched_rows": _delta(slice_h, slice_ndjson_h, "matched_rows"),
            "coverage_ratio": _delta(slice_h, slice_ndjson_h, "coverage_ratio"),
            "composite_score": _delta(slice_h, slice_ndjson_h, "composite_score"),
        }

    if prod_ndjson_h is not None:
        payload["arms"]["production_plus_ndjson_context"] = {
            "news_jsonl": str(prod_ndjson_news),
            "merged_row_count": prod_ndjson_row_count,
            "ndjson_context_jsonl": str(args.ndjson_context_jsonl),
            "news_row_count": prod_plus_ndjson_eval.get("inputs", {}).get("news_row_count")
            if prod_plus_ndjson_eval
            else None,
            "hypothesis": prod_ndjson_h,
        }
        payload["delta_prod_plus_ndjson_minus_production"] = {
            "matched_rows": _delta(prod_h, prod_ndjson_h, "matched_rows"),
            "coverage_ratio": _delta(prod_h, prod_ndjson_h, "coverage_ratio"),
            "composite_score": _delta(prod_h, prod_ndjson_h, "composite_score"),
        }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json), "hypothesis_id": hyp_id}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
