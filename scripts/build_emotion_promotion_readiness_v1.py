#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List


def _iter_jsonl(path: Path) -> Iterable[Dict[str, Any]]:
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except Exception:
            continue
        if isinstance(row, dict):
            yield row


def main() -> int:
    ap = argparse.ArgumentParser(description="Build rolling promotion readiness from weekly history.")
    ap.add_argument("--history-jsonl", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--window-size", type=int, default=4)
    args = ap.parse_args()

    rows: List[Dict[str, Any]] = list(_iter_jsonl(args.history_jsonl))
    window = max(1, args.window_size)
    tail = rows[-window:]
    passed = [
        r for r in tail if str(((r.get("source_gate") or {}).get("combined_recommended"))) == "candidate_for_btrack_promotion"
    ]
    readiness = {
        "schema_version": "emotion_promotion_readiness_v1",
        "window_size": window,
        "n_history": len(rows),
        "n_window": len(tail),
        "n_passed_in_window": len(passed),
        "required_consecutive_passes": window,
        "ready_for_human_gate": (len(tail) == window and len(passed) == window),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(readiness, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
