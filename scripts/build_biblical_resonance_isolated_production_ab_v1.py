#!/usr/bin/env python3
"""Isolated production A/B: prod ledger minus slice/NDJSON overlap, then prod+NDJSON merge.

research_only · [HYPO] · operational (post-processor) repair arm is prod_clean+NDJSON only.
"""

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
DEFAULT_PROD = ROOT / "docs/final/artifacts/news_observation_v1_latest.jsonl"
DEFAULT_SLICE = ROOT / "docs/final/artifacts/news_observation_v1_biblical_history_research_slice_latest.jsonl"
DEFAULT_NDJSON = ROOT / "docs/final/artifacts/news_observation_v1_dss_ndjson_research_context_latest.jsonl"
DEFAULT_OUT = ROOT / "reports/biblical_resonance_isolated_production_ab_latest.json"

_EXCLUDE_SOURCE_PREFIXES = ("dss_ndjson_", "dss_apocrypha_", "dss_ndjson_ingest")


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


def _write_jsonl(rows: list[dict[str, Any]], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + ("\n" if rows else ""),
        encoding="utf-8",
    )
    return len(rows)


def _isolate_production(
    prod_rows: list[dict[str, Any]],
    *,
    slice_rows: list[dict[str, Any]],
    ndjson_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    slice_keys = {_row_key(r) for r in slice_rows if _row_key(r)}
    ndjson_keys = {_row_key(r) for r in ndjson_rows if _row_key(r)}
    overlap_slice = 0
    overlap_ndjson = 0
    overlap_source = 0
    isolated: list[dict[str, Any]] = []
    for row in prod_rows:
        key = _row_key(row)
        sid = str(row.get("source_id") or "")
        if key and key in slice_keys:
            overlap_slice += 1
            continue
        if key and key in ndjson_keys:
            overlap_ndjson += 1
            continue
        if any(sid.startswith(p) for p in _EXCLUDE_SOURCE_PREFIXES):
            overlap_source += 1
            continue
        isolated.append(row)
    stats = {
        "production_total": len(prod_rows),
        "production_isolated": len(isolated),
        "removed_overlap_slice_keys": overlap_slice,
        "removed_overlap_ndjson_keys": overlap_ndjson,
        "removed_dss_source_prefix": overlap_source,
    }
    return isolated, stats


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
    return _write_jsonl(merged, out_path)


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


def _hyp_row(doc: dict[str, Any], hyp_id: str) -> dict[str, Any]:
    for row in doc.get("hypotheses") or []:
        if isinstance(row, dict) and row.get("id") == hyp_id:
            return row
    return {}


def _delta(a: dict[str, Any], b: dict[str, Any], key: str) -> float | None:
    av = a.get(key)
    bv = b.get(key)
    if isinstance(av, (int, float)) and isinstance(bv, (int, float)):
        return round(float(bv) - float(av), 6)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--production-news-jsonl", type=Path, default=DEFAULT_PROD)
    ap.add_argument("--research-slice-jsonl", type=Path, default=DEFAULT_SLICE)
    ap.add_argument("--ndjson-context-jsonl", type=Path, default=DEFAULT_NDJSON)
    ap.add_argument("--lookback-days", type=int, default=90)
    ap.add_argument("--hypothesis-id", default="H-DSS1")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    prod_rows = _load_jsonl(args.production_news_jsonl)
    slice_rows = _load_jsonl(args.research_slice_jsonl)
    ndjson_rows = _load_jsonl(args.ndjson_context_jsonl)
    isolated_rows, isolation_stats = _isolate_production(
        prod_rows, slice_rows=slice_rows, ndjson_rows=ndjson_rows
    )

    tmp_dir = Path(tempfile.mkdtemp(prefix="biblical_isolated_ab_"))
    isolated_news = tmp_dir / "production_isolated.jsonl"
    merged_news = tmp_dir / "production_isolated_plus_ndjson.jsonl"
    _write_jsonl(isolated_rows, isolated_news)

    raw_eval = _run_eval(isolated_news, tmp_dir / "raw_eval.json", args.lookback_days)
    repair_eval: dict[str, Any] | None = None
    merged_count = 0
    if args.ndjson_context_jsonl.is_file():
        merged_count = _merge_jsonl([isolated_news, args.ndjson_context_jsonl], merged_news)
        repair_eval = _run_eval(merged_news, tmp_dir / "repair_eval.json", args.lookback_days)

    hyp_id = args.hypothesis_id
    raw_h = _hyp_row(raw_eval, hyp_id)
    repair_h = _hyp_row(repair_eval, hyp_id) if repair_eval else {}

    payload = {
        "schema": "biblical_resonance_isolated_production_ab_v1",
        "generated_at_utc": _utc_now(),
        "research_rail": "B",
        "hypothesis_tier": "[HYPO]",
        "gating_status": "NON_GATING",
        "hypothesis_id": hyp_id,
        "window_days": args.lookback_days,
        "isolation": isolation_stats,
        "raw": {
            "arm": "production_isolated",
            "news_jsonl": str(isolated_news),
            "news_row_count": raw_eval.get("inputs", {}).get("news_row_count"),
            "matched_rows": raw_h.get("matched_rows"),
            "coverage_ratio": raw_h.get("coverage_ratio"),
            "composite_score": raw_h.get("composite_score"),
        },
        "repair_v2": {
            "arm": "production_isolated_plus_ndjson_context",
            "label": "operational (post-processor included)",
            "news_jsonl": str(merged_news),
            "merged_row_count": merged_count,
            "news_row_count": repair_eval.get("inputs", {}).get("news_row_count") if repair_eval else None,
            "matched_rows": repair_h.get("matched_rows"),
            "coverage_ratio": repair_h.get("coverage_ratio"),
            "composite_score": repair_h.get("composite_score"),
        },
        "delta": {
            "alignment_pass_rate_delta_repair_v2_minus_raw": _delta(raw_h, repair_h, "composite_score"),
            "matched_rows": _delta(raw_h, repair_h, "matched_rows"),
            "coverage_ratio": _delta(raw_h, repair_h, "coverage_ratio"),
        },
        "interpretation": {
            "status": "research_only_not_promotion_proof",
            "note": "Isolated prod removes slice/NDJSON key overlap before repair merge; not Track A gate proof.",
        },
        "track_a_promotion": "blocked",
        "live_trading_trigger": "forbidden",
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "output": str(args.output_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
