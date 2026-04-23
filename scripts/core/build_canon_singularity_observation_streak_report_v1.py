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
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_md(path: Path, data: dict[str, Any]) -> None:
    metrics = data.get("metrics") or {}
    lines = [
        "# Canon Observation Streak Report v1",
        "",
        f"- generated_at_utc: {data.get('generated_at_utc')}",
        f"- verdict: {data.get('verdict')}",
        f"- window: {metrics.get('window')}",
        f"- pass_count: {metrics.get('pass_count')}",
        f"- hold_count: {metrics.get('hold_count')}",
        f"- pass_rate: {metrics.get('pass_rate')}",
        f"- latest_verdict: {metrics.get('latest_verdict')}",
        "",
        "## Hold Reasons (window)",
    ]
    hold_reasons = data.get("hold_reasons") or {}
    if hold_reasons:
        for key in sorted(hold_reasons.keys()):
            lines.append(f"- {key}: {hold_reasons[key]}")
    else:
        lines.append("- none")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Build rolling streak report from nextday observation history.")
    ap.add_argument(
        "--history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_nextday_observation_history_v1.jsonl",
    )
    ap.add_argument("--window", type=int, default=3)
    ap.add_argument("--min-pass-count", type=int, default=3)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_observation_streak_report_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_observation_streak_report_v1.md",
    )
    args = ap.parse_args()

    rows = _read_jsonl(Path(args.history_jsonl))
    tail = rows[-args.window :] if args.window > 0 else rows[:]
    pass_count = sum(1 for x in tail if str(x.get("verdict") or "") == "pass")
    hold_count = len(tail) - pass_count
    hold_reasons: dict[str, int] = {}
    for row in tail:
        for reason in row.get("hold_reasons") or []:
            hold_reasons[reason] = hold_reasons.get(reason, 0) + 1
    latest_verdict = str(tail[-1].get("verdict") or "unknown") if tail else "unknown"
    enough_rows = len(tail) >= args.window
    verdict = "pass" if enough_rows and pass_count >= args.min_pass_count and latest_verdict == "pass" else "hold"
    out = {
        "schema": "original_corpus_regime_singularity_canon_observation_streak_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "history_jsonl": str(args.history_jsonl),
            "window": args.window,
            "min_pass_count": args.min_pass_count,
        },
        "verdict": verdict,
        "metrics": {
            "window": args.window,
            "window_size_observed": len(tail),
            "pass_count": pass_count,
            "hold_count": hold_count,
            "pass_rate": round((pass_count / len(tail)), 6) if tail else 0.0,
            "latest_verdict": latest_verdict,
        },
        "hold_reasons": hold_reasons,
    }
    _write_json(Path(args.output_json), out)
    _write_md(Path(args.output_md), out)
    print(str(args.output_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

