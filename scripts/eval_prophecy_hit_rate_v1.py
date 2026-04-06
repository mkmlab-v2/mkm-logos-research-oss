#!/usr/bin/env python3
"""Prophecy hit-rate eval v1 — B-Track measurement only; does not touch live trading.

run_mode:
  price  — compare predicted vs actual direction using a small scoring payload (local SSOT).
  proxy  — optional registry/oracle precision path (placeholder until wired).

Default out: docs/final/artifacts/prophecy_hit_rate_eval_latest.json
See: docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md (Prophecy Hit Rate CLI).
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "prophecy_hit_rate_eval_latest.json"
SCHEMA = "prophecy_hit_rate_eval_report_v2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return o if isinstance(o, dict) else None


def _eval_price(score_path: Path | None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Single or batch rows: {predicted_direction, actual_direction} or {rows:[...]}."""
    if not score_path or not score_path.is_file():
        return (
            {"price_directional_hit_rate": None, "n_evaluated": 0},
            {"status": "no_data", "zeroing_note": "price: pass --score-json with predicted/actual directions."},
        )
    doc = _load_json(score_path)
    if not doc:
        return (
            {"price_directional_hit_rate": None, "n_evaluated": 0},
            {"status": "invalid_input", "zeroing_note": "score-json not valid JSON object."},
        )

    rows: list[dict[str, Any]]
    if "rows" in doc and isinstance(doc["rows"], list):
        rows = [r for r in doc["rows"] if isinstance(r, dict)]
    else:
        rows = [doc]

    hits = 0
    n = 0
    for r in rows:
        pd = str(r.get("predicted_direction") or r.get("predicted_sign") or "").strip().lower()
        ad = str(r.get("actual_direction") or r.get("actual_sign") or "").strip().lower()
        if not pd or not ad:
            continue
        if pd not in ("bull", "bear", "neutral") or ad not in ("bull", "bear", "neutral"):
            continue
        n += 1
        if pd == ad:
            hits += 1

    if n == 0:
        return (
            {"price_directional_hit_rate": None, "n_evaluated": 0},
            {"status": "no_data", "zeroing_note": "No comparable direction pairs in score-json."},
        )

    rate = hits / n
    return (
        {"price_directional_hit_rate": round(rate, 6), "n_evaluated": n, "price_hits": hits},
        {"status": "ok", "zeroing_note": "price: directional match rate over provided rows."},
    )


def _eval_proxy(registry_glob: str | None, root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    if not registry_glob:
        return (
            {"proxy_hit_rate": None, "n_evaluated": 0},
            {
                "status": "no_data",
                "zeroing_note": "proxy: set --registry-glob or wire explicit registry JSON (precision ≠ price hit).",
            },
        )
    matches = list(root.glob(registry_glob))
    if not matches:
        return (
            {"proxy_hit_rate": None, "n_evaluated": 0},
            {"status": "no_data", "zeroing_note": f"proxy: no files for glob {registry_glob!r}"},
        )
    return (
        {"proxy_hit_rate": None, "n_evaluated": 0, "registry_candidates": [str(p) for p in matches[:20]]},
        {
            "status": "no_data",
            "zeroing_note": "proxy: registry files found; precision extraction not implemented in v1 stub.",
        },
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Prophecy hit rate eval v2 report writer (B-Track).")
    ap.add_argument(
        "--run-mode",
        choices=("price", "proxy"),
        default="proxy",
        help="price: directional scoring via --score-json; proxy: registry/oracle placeholder",
    )
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true", help="Print JSON to stdout; do not write file.")
    ap.add_argument(
        "--score-json",
        type=Path,
        default=None,
        help="price mode: JSON with predicted_direction & actual_direction (or rows[]).",
    )
    ap.add_argument(
        "--registry-glob",
        type=str,
        default=None,
        help="proxy mode: glob under workspace root for registry reports (optional).",
    )
    args = ap.parse_args()

    if args.run_mode == "price":
        metrics, meta = _eval_price(args.score_json)
    else:
        metrics, meta = _eval_proxy(args.registry_glob, ROOT)

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "generated_at_utc": _utc_now(),
        "run_mode": args.run_mode,
        "status": meta.get("status", "unknown"),
        "zeroing_note": meta.get(
            "zeroing_note",
            "price: directional hit rate vs forward return from OHLCV; proxy: registry/oracle precision — not identical to price hit rate.",
        ),
        "inputs": {
            "run_mode": args.run_mode,
            "score_json": str(args.score_json) if args.score_json else None,
            "registry_glob": args.registry_glob,
        },
        "metrics": metrics,
        "sources": {
            "oracle_path": None,
            "registry_path": None,
            "used_field": None,
        },
    }

    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    print(text)
    if not args.stdout_only:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.output.resolve()}", file=__import__("sys").stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
