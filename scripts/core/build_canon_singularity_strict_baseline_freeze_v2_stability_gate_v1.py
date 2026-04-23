#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s:
            continue
        rows.append(json.loads(s))
    return rows


def _write_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    m = data.get("metrics") or {}
    c = data.get("checks") or {}
    lines = [
        "# Canon Strict Baseline Freeze V2 Stability Gate v1",
        "",
        f"- generated_at_utc: {data.get('generated_at_utc')}",
        f"- status: {data.get('status')}",
        "",
        "## Metrics",
        f"- window_size: {m.get('window_size')}",
        f"- frozen_count: {m.get('frozen_count')}",
        f"- rolled_count: {m.get('rolled_count')}",
        f"- noop_hold_count: {m.get('noop_hold_count')}",
        f"- frozen_rate: {m.get('frozen_rate')}",
        "",
        "## Checks",
        f"- history_present_ok: {c.get('history_present_ok')}",
        f"- window_size_ok: {c.get('window_size_ok')}",
        f"- frozen_rate_ok: {c.get('frozen_rate_ok')}",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate freeze v2 frozen-rate stability gate from rollover history.")
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_rollover_history_v1.jsonl",
    )
    ap.add_argument("--window", type=int, default=7)
    ap.add_argument("--min-window-size", type=int, default=5)
    ap.add_argument("--min-frozen-rate", type=float, default=0.85)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1.md",
    )
    args = ap.parse_args()

    rows = _read_jsonl(Path(args.history_jsonl))
    window = max(1, int(args.window))
    recent = rows[-window:]
    n = len(recent)
    frozen_count = sum(1 for r in recent if str(r.get("freeze_decision") or "") == "frozen")
    rolled_count = sum(1 for r in recent if str(r.get("rollover_status") or "") == "rolled")
    noop_hold_count = sum(1 for r in recent if str(r.get("rollover_status") or "") == "noop_hold")
    frozen_rate = (frozen_count / n) if n > 0 else 0.0
    min_window_size = max(1, int(args.min_window_size))

    checks = {
        "history_present_ok": n > 0,
        "window_size_ok": n >= min_window_size,
        "frozen_rate_ok": (frozen_rate >= float(args.min_frozen_rate)) if (n >= min_window_size) else False,
    }
    status = "pass" if all(checks.values()) else "fail"

    out = {
        "schema": "original_corpus_regime_singularity_canon_strict_baseline_freeze_v2_stability_gate_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "history_jsonl": str(args.history_jsonl),
            "window": window,
            "min_window_size": min_window_size,
            "min_frozen_rate": float(args.min_frozen_rate),
        },
        "status": status,
        "checks": checks,
        "metrics": {
            "window_size": n,
            "frozen_count": frozen_count,
            "rolled_count": rolled_count,
            "noop_hold_count": noop_hold_count,
            "frozen_rate": round(frozen_rate, 6),
        },
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

