#!/usr/bin/env python3
"""Report numeric-symbol injection matches against curated symbol candidates."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PILOT = ROOT / "reports" / "constitution" / "btrack_pilot"
DEFAULT_INPUT = PILOT / "symbol_candidates_curated_stable_latest.jsonl"
DEFAULT_TEMPLATE = ROOT / "data" / "logos" / "btrack_pilot" / "gates" / "symbol_numeric_seed_v1.json"
DEFAULT_OUTPUT = PILOT / "symbol_numeric_injection_latest.json"


def _abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _iter_jsonl(path: Path):
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            if isinstance(obj, dict):
                yield obj


def _load_numeric_template(path: Path) -> dict[str, dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("symbols", [])
    out: dict[str, dict[str, Any]] = {}
    if not isinstance(rows, list):
        return out
    for row in rows:
        if not isinstance(row, dict):
            continue
        sym = str(row.get("symbol", "")).strip()
        if not sym:
            continue
        out[sym] = row
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Report numeric-symbol injection coverage")
    ap.add_argument("--input-jsonl", default=str(DEFAULT_INPUT))
    ap.add_argument("--numeric-template", default=str(DEFAULT_TEMPLATE))
    ap.add_argument("--out-json", default=str(DEFAULT_OUTPUT))
    args = ap.parse_args()

    input_path = _abs(args.input_jsonl)
    template_path = _abs(args.numeric_template)
    out_path = _abs(args.out_json)

    for p in (input_path, template_path):
        if not p.is_file():
            print(f"ERROR: missing file: {p}")
            return 2

    seed_map = _load_numeric_template(template_path)
    found: list[dict[str, Any]] = []
    curated_count = 0
    for row in _iter_jsonl(input_path):
        curated_count += 1
        symbol = str(row.get("symbol", "")).strip()
        if symbol in seed_map:
            seed = seed_map[symbol]
            found.append(
                {
                    "symbol": symbol,
                    "label": seed.get("label", ""),
                    "category": seed.get("category", "numerical"),
                    "priority": seed.get("priority", "medium"),
                    "score_tfidf_like": float(row.get("score_tfidf_like", 0.0) or 0.0),
                    "source_mix": row.get("source_mix", {}),
                }
            )

    found.sort(key=lambda r: (-float(r.get("score_tfidf_like", 0.0)), str(r.get("symbol", ""))))
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    payload = {
        "schema": "symbol_numeric_injection_report_v1",
        "generated_at_utc": ts,
        "inputs": {
            "curated_jsonl": str(input_path),
            "numeric_template": str(template_path),
        },
        "stats": {
            "curated_count": curated_count,
            "numeric_seed_count": len(seed_map),
            "matched_count": len(found),
            "coverage_rate": (len(found) / len(seed_map)) if seed_map else 0.0,
        },
        "matches": found,
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
