#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


_ROW_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)$")


def _slice_key(row_id: str) -> str:
    m = _ROW_RE.match(row_id)
    if not m:
        return "unknown"
    return f"{m.group(1)}.{m.group(2)}"


def _slice_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        k = _slice_key(str(r.get("row_id") or ""))
        out[k] = out.get(k, 0) + 1
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build slice stability monitor from insight history.")
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_history_v1.jsonl",
    )
    ap.add_argument("--window", type=int, default=3)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_slice_stability_v1.json",
    )
    args = ap.parse_args()

    hist = _read_jsonl(Path(args.history_jsonl))
    recent = hist[-int(args.window) :] if hist else []
    latest = recent[-1] if recent else {}
    prev = recent[-2] if len(recent) >= 2 else {}
    latest_rows = list((latest or {}).get("insights") or [])
    prev_rows = list((prev or {}).get("insights") or [])
    latest_counts = _slice_counts(latest_rows)
    prev_counts = _slice_counts(prev_rows)
    keys = sorted(set(latest_counts.keys()) | set(prev_counts.keys()))
    changes: list[dict[str, Any]] = []
    for k in keys:
        a = int(latest_counts.get(k, 0))
        b = int(prev_counts.get(k, 0))
        if a != b:
            changes.append({"slice": k, "prev_count": b, "latest_count": a, "delta": a - b})

    out = {
        "schema": "original_corpus_regime_singularity_canon_insight_slice_stability_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {"history_jsonl": str(args.history_jsonl), "window": int(args.window)},
        "counts": {
            "history_events_total": len(hist),
            "events_in_window": len(recent),
            "latest_rows": len(latest_rows),
            "prev_rows": len(prev_rows),
            "slice_change_count": len(changes),
        },
        "latest_generated_at_utc": (latest or {}).get("generated_at_utc"),
        "prev_generated_at_utc": (prev or {}).get("generated_at_utc"),
        "latest_slice_counts": latest_counts,
        "slice_changes": changes,
    }
    out_path = Path(args.output_json)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

