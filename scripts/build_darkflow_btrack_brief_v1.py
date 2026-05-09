#!/usr/bin/env python3
"""Build a human-readable brief from Dark Flow B-track gate output."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_gate_latest.json"
DEFAULT_OUT_MD = ROOT / "docs" / "final" / "artifacts" / "darkflow_btrack_brief_latest.md"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fmt(value: Any) -> str:
    try:
        return f"{float(value):.3f}"
    except (TypeError, ValueError):
        return "n/a"


def main() -> int:
    ap = argparse.ArgumentParser(description="Build Dark Flow B-track brief markdown.")
    ap.add_argument("--gate-json", type=Path, default=DEFAULT_GATE)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    args = ap.parse_args()

    if not args.gate_json.exists():
        raise FileNotFoundError(f"Missing gate json: {args.gate_json}")

    gate = _load(args.gate_json)
    ranked = gate.get("ranked_hypotheses", [])
    if not isinstance(ranked, list):
        ranked = []

    now_utc = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    lines: list[str] = []
    lines.append("# Dark Flow B-track Brief (Latest)")
    lines.append("")
    lines.append(f"- generated_at_utc: `{now_utc}`")
    lines.append(f"- checked_at_utc: `{gate.get('checked_at_utc', 'n/a')}`")
    lines.append(f"- decision: `{gate.get('decision', 'n/a')}`")
    lines.append(f"- source_track: `{gate.get('source_track', 'n/a')}`")
    lines.append(f"- observation_mode: `{gate.get('observation_mode', 'n/a')}`")
    lines.append("")
    lines.append("## Gate Metrics")
    lines.append("")
    lines.append(f"- hypotheses_count: `{gate.get('hypotheses_count', 'n/a')}`")
    lines.append(f"- supported_datasets_count: `{gate.get('supported_datasets_count', 'n/a')}`")
    lines.append(f"- mean_replication_score: `{_fmt(gate.get('mean_replication_score'))}`")
    lines.append(f"- mean_systematic_risk: `{_fmt(gate.get('mean_systematic_risk'))}`")
    lines.append(f"- best_composite_score: `{_fmt(gate.get('best_composite_score'))}`")
    lines.append("")

    failures = gate.get("failures", [])
    if isinstance(failures, list) and failures:
        lines.append("## Blocking Failures")
        lines.append("")
        for f in failures:
            lines.append(f"- `{f}`")
    else:
        lines.append("## Blocking Failures")
        lines.append("")
        lines.append("- none")

    lines.append("")
    lines.append("## Ranked Hypotheses")
    lines.append("")
    if ranked:
        for idx, row in enumerate(ranked, start=1):
            if not isinstance(row, dict):
                continue
            lines.append(
                f"{idx}. `{row.get('id', 'n/a')}` {row.get('label', 'n/a')} "
                f"(composite={_fmt(row.get('composite_score'))}, "
                f"replication={_fmt(row.get('replication_score'))}, "
                f"risk={_fmt(row.get('systematic_risk'))})"
            )
    else:
        lines.append("- no ranked hypotheses available")
    lines.append("")
    lines.append("## Interpretation")
    lines.append("")
    lines.append("- This output is B-track research evidence only.")
    lines.append("- No A-track binding or production trigger is allowed from this artifact.")
    lines.append("- Use this ranking to prioritize further data collection and re-evaluation.")
    lines.append("")

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    args.output_md.write_text("\n".join(lines), encoding="utf-8")
    print(str(args.output_md))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
