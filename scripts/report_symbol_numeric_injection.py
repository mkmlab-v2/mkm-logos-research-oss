#!/usr/bin/env python3
"""Report numeric-symbol injection matches against curated symbol candidates."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))

from scripts.core.sovereign_jsonl import iter_jsonl_dict_rows  # noqa: E402
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_INPUT = PILOT / "symbol_candidates_curated_stable_latest.jsonl"
DEFAULT_RAW_INPUT = PILOT / "symbol_candidates_stable_latest.jsonl"
DEFAULT_TEMPLATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_numeric_seed_v1.json"
DEFAULT_OUTPUT = PILOT / "symbol_numeric_injection_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    """B-track pilot JSONL: use Track B context (no Track A row guard)."""
    yield from iter_jsonl_dict_rows(path, track_context="B")


def _normalize_symbol(value: str) -> str:
    return " ".join(str(value).strip().lower().replace(",", "").split())


def _load_numeric_template(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, str]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("symbols", [])
    out: dict[str, dict[str, Any]] = {}
    alias_to_seed: dict[str, str] = {}
    if not isinstance(rows, list):
        return out, alias_to_seed
    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol", "")).strip()
        if not sym:
            continue
        out[sym] = row
        canonical = _normalize_symbol(sym)
        if canonical:
            alias_to_seed[canonical] = sym
        aliases = row.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                key = _normalize_symbol(str(alias))
                if key:
                    alias_to_seed[key] = sym
    return out, alias_to_seed


def _build_near_miss_candidates(
    rows: list[dict[str, Any]],
    missing_symbols: list[str],
    alias_to_seed: dict[str, str],
) -> dict[str, list[dict[str, Any]]]:
    pattern_map: dict[str, re.Pattern[str]] = {
        "7": re.compile(r"שבע"),
        "70": re.compile(r"שבע(ים)?"),
        "144000": re.compile(r"(מאה|אלף)"),
    }
    reason_map = {
        "7": "Contains Hebrew root 'שבע' but may be oath/verb form, not confirmed numeral.",
        "70": "Contains Hebrew seven-family token but lacks explicit canonical seventy form.",
        "144000": "Contains thousand/hundred token family but not explicit 144000 expression.",
    }
    out: dict[str, list[dict[str, Any]]] = {}
    for seed_symbol in missing_symbols:
        pat = pattern_map.get(seed_symbol)
        if not pat:
            continue
        bucket: list[dict[str, Any]] = []
        seen: set[str] = set()
        for row in rows:
            symbol_raw = str(row.get("symbol", "")).strip()
            if not symbol_raw:
                continue
            normalized = _normalize_symbol(symbol_raw)
            if normalized in alias_to_seed:
                continue
            if not pat.search(normalized):
                continue
            if normalized in seen:
                continue
            seen.add(normalized)
            bucket.append(
                {
                    "candidate": symbol_raw,
                    "score_tfidf_like": float(row.get("score_tfidf_like", 0.0) or 0.0),
                    "source_mix": row.get("source_mix", {}),
                    "reason": reason_map.get(seed_symbol, "Near-miss token family detected."),
                }
            )
        bucket.sort(key=lambda r: -float(r.get("score_tfidf_like", 0.0)))
        if bucket:
            out[seed_symbol] = bucket[:5]
    return out


def _build_p1_manual_review_queue(
    near_miss: dict[str, list[dict[str, Any]]],
    generated_at_utc: str,
) -> list[dict[str, Any]]:
    queue: list[dict[str, Any]] = []
    for seed_symbol, candidates in near_miss.items():
        for row in candidates:
            queue.append(
                {
                    "id": f"numeric-near-miss-{seed_symbol}-{_normalize_symbol(str(row.get('candidate', '')))}",
                    "priority": "P1",
                    "status": "pending_manual_review",
                    "seed_symbol": seed_symbol,
                    "candidate": row.get("candidate", ""),
                    "reason": row.get("reason", ""),
                    "score_tfidf_like": float(row.get("score_tfidf_like", 0.0) or 0.0),
                    "source_mix": row.get("source_mix", {}),
                    "promotion_guard": "approve_numeric_near_miss=true required",
                    "created_at_utc": generated_at_utc,
                }
            )
    queue.sort(key=lambda r: -float(r.get("score_tfidf_like", 0.0)))
    return queue


def main() -> int:
    ap = argparse.ArgumentParser(description="Report numeric-symbol injection coverage")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument(
        "--raw-jsonl",
        default=str(DEFAULT_RAW_INPUT),
        help="Optional raw candidate pool for wider near-miss diagnostics.",
    )
    ap.add_argument("--numeric-template", default=str(DEFAULT_TEMPLATE))
    ap.add_argument("--out-json", default=str(DEFAULT_OUTPUT))
    args = ap.parse_args()

    input_path = _abs(args.input_jsonl)
    raw_path = _abs(args.raw_jsonl) if str(args.raw_jsonl).strip() else None
    template_path = _abs(args.numeric_template)
    out_path = _abs(args.out_json)

    for p in (input_path, template_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2
    if raw_path and (not raw_path.is_file()):
        raw_path = None

    seed_map, alias_to_seed = _load_numeric_template(template_path)
    found_by_seed: dict[str, dict[str, Any]] = {}
    curated_rows: list[dict[str, Any]] = []
    curated_count = 0
    for row in _iter_jsonl(input_path):
        curated_count += 1
        curated_rows.append(row)
        symbol_raw = str(row.get("symbol", "")).strip()
        symbol = _normalize_symbol(symbol_raw)
        seed_symbol = alias_to_seed.get(symbol)
        if not seed_symbol:
            continue
        seed = seed_map.get(seed_symbol, {})
        score = float(row.get("score_tfidf_like", 0.0) or 0.0)
        prev = found_by_seed.get(seed_symbol)
        if prev and float(prev.get("score_tfidf_like", 0.0) or 0.0) >= score:
            continue
        found_by_seed[seed_symbol] = {
            "symbol": seed_symbol,
            "matched_candidate": symbol_raw,
            "label": seed.get("label", ""),
            "category": seed.get("category", "numerical"),
            "priority": seed.get("priority", "medium"),
            "score_tfidf_like": score,
            "source_mix": row.get("source_mix", {}),
        }

    found = list(found_by_seed.values())
    found.sort(key=lambda r: (-float(r.get("score_tfidf_like", 0.0)), str(r.get("symbol", ""))))
    missing = [sym for sym in seed_map.keys() if sym not in found_by_seed]
    near_miss_rows = list(curated_rows)
    if raw_path:
        near_miss_rows = list(_iter_jsonl(raw_path))
    near_miss = _build_near_miss_candidates(near_miss_rows, missing, alias_to_seed)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    manual_review_queue = _build_p1_manual_review_queue(near_miss, ts)
    payload = {
        "schema": "symbol_numeric_injection_report_v1",
        "generated_at_utc": ts,
        "inputs": {
            "curated_jsonl": str(input_path),
            "raw_jsonl": str(raw_path) if raw_path else None,
            "numeric_template": str(template_path),
        },
        "stats": {
            "curated_count": curated_count,
            "numeric_seed_count": len(seed_map),
            "matched_count": len(found),
            "coverage_rate": (len(found) / len(seed_map)) if seed_map else 0.0,
            "near_miss_scan_rows": len(near_miss_rows),
        },
        "matches": found,
        "missing_symbols": missing,
        "near_miss_candidates": near_miss,
        "p1_manual_review_queue": manual_review_queue,
        "promotion_policy": {
            "near_miss_auto_promotion": False,
            "required_approval_flag": "approve_numeric_near_miss=true",
        },
        "note": "Numeric symbol injection report is an operational seed match, not doctrinal certainty.",
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("OK: numeric symbol injection report generated")
    print(f"out={out_path}")
    print(f"matched={len(found)}/{len(seed_map)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
