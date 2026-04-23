#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
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


def _index(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(r.get("row_id")): r for r in rows if r.get("row_id")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build weekly brief from canon insight/gate artifacts.")
    ap.add_argument(
        "--insight-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_minimum_history_v1.jsonl",
    )
    ap.add_argument(
        "--gate-history-jsonl",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_history_v1.jsonl",
    )
    ap.add_argument(
        "--health-summary-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_quality_gate_health_summary_v1.json",
    )
    ap.add_argument(
        "--slice-stability-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_insight_slice_stability_v1.json",
    )
    ap.add_argument("--window", type=int, default=7)
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_weekly_brief_v1.json",
    )
    ap.add_argument(
        "--output-md",
        default="docs/final/artifacts/original_corpus_regime_singularity_canon_weekly_brief_v1.md",
    )
    args = ap.parse_args()

    insight_hist = _read_jsonl(Path(args.insight_history_jsonl))
    gate_hist = _read_jsonl(Path(args.gate_history_jsonl))
    health = _read_json(Path(args.health_summary_json))
    slice_stab = _read_json(Path(args.slice_stability_json))
    w = int(args.window)

    insight_recent = insight_hist[-w:]
    gate_recent = gate_hist[-w:]
    latest = insight_recent[-1] if insight_recent else {}
    prev = insight_recent[-2] if len(insight_recent) >= 2 else {}
    latest_rows = list((latest or {}).get("insights") or [])
    prev_rows = list((prev or {}).get("insights") or [])

    li = _index(latest_rows)
    pi = _index(prev_rows)
    added_ids = sorted(set(li.keys()) - set(pi.keys()))[:10]
    removed_ids = sorted(set(pi.keys()) - set(li.keys()))[:10]

    gate_pass = sum(1 for g in gate_recent if g.get("result") == "pass")
    gate_fail = sum(1 for g in gate_recent if g.get("result") == "fail")
    dominant_regime = (latest.get("meta") or {}).get("dominant_regime_in_top_n")

    out = {
        "schema": "original_corpus_regime_singularity_canon_weekly_brief_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inputs": {
            "window": w,
            "insight_history_jsonl": str(args.insight_history_jsonl),
            "gate_history_jsonl": str(args.gate_history_jsonl),
        },
        "counts": {
            "insight_events_in_window": len(insight_recent),
            "gate_events_in_window": len(gate_recent),
            "gate_pass_count": gate_pass,
            "gate_fail_count": gate_fail,
            "added_top10_count": len(added_ids),
            "removed_top10_count": len(removed_ids),
        },
        "highlights": {
            "dominant_regime_latest": dominant_regime,
            "health_level": health.get("health_level"),
            "slice_change_count": (slice_stab.get("counts") or {}).get("slice_change_count"),
        },
        "added_top10": [li[i] for i in added_ids],
        "removed_top10": [pi[i] for i in removed_ids],
    }
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md = [
        "# Canon Weekly Brief v1",
        f"- generated_at_utc: {out['generated_at_utc']}",
        f"- dominant_regime_latest: {dominant_regime}",
        f"- health_level: {health.get('health_level')}",
        f"- gate pass/fail (window={w}): {gate_pass}/{gate_fail}",
        f"- slice_change_count: {(slice_stab.get('counts') or {}).get('slice_change_count')}",
        "",
        "## Added Top 10",
    ]
    for r in out["added_top10"]:
        md.append(f"- {r.get('row_id')} ({r.get('best_regime')}, score={r.get('score')})")
    md.append("")
    md.append("## Removed Top 10")
    for r in out["removed_top10"]:
        md.append(f"- {r.get('row_id')} ({r.get('best_regime')}, score={r.get('score')})")
    out_md = Path(args.output_md)
    out_md.parent.mkdir(parents=True, exist_ok=True)
    out_md.write_text("\n".join(md) + "\n", encoding="utf-8")

    print(str(out_json))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

