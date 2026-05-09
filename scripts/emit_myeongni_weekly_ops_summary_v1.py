#!/usr/bin/env python3
"""Write a thin markdown pointer summary for Myeongni weekly ops (SSOT remains JSON)."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
REPORTS = ROOT / "reports"


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lens-json", type=Path, default=ART / "myeongni_independent_lens_latest.json")
    ap.add_argument("--gate-json", type=Path, default=ART / "independent_lens_shadow_gate_latest.json")
    ap.add_argument(
        "--probe-json",
        type=Path,
        default=None,
        help="Optional 16_STATE_MASTER_PROBE JSON (coverage_summary.states_with_audit).",
    )
    ap.add_argument("--out", type=Path, default=REPORTS / "myeongni_weekly_ops_summary_latest.md")
    args = ap.parse_args()

    lens = _read_json(args.lens_json)
    gate = _read_json(args.gate_json)
    probe = _read_json(args.probe_json) if args.probe_json else {}

    scores = lens.get("scores") if isinstance(lens.get("scores"), dict) else {}
    ds = scores.get("direction_score")
    hist = gate.get("history") if isinstance(gate.get("history"), dict) else {}
    cov = probe.get("coverage_summary") if isinstance(probe.get("coverage_summary"), dict) else {}

    gen = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = [
        "# Myeongni weekly ops summary (pointer only)",
        "",
        f"- summary_generated_at_utc: `{gen}`",
        "- ssot_note: Numeric truth is in the JSON paths below; this file is not a governance SSOT.",
        "",
        "## Step 1 — Independent lens",
        f"- path: `{args.lens_json.as_posix()}`",
        f"- ts_utc (artifact): `{lens.get('ts_utc', 'MISSING')}`",
        f"- schema: `{lens.get('schema', 'MISSING')}`",
        f"- direction_score: `{ds}`",
        "",
        "## Step 2 — Shadow gate (weekly KPI lock-on)",
        f"- path: `{args.gate_json.as_posix()}`",
        f"- ts_utc (artifact): `{gate.get('ts_utc', 'MISSING')}`",
        f"- decision: `{gate.get('decision', 'MISSING')}`",
        f"- blockers: `{json.dumps(gate.get('blockers'), ensure_ascii=False)}`",
        f"- weekly_cycles_observed: `{hist.get('weekly_cycles_observed', 'MISSING')}`",
        f"- monthly_cycles_observed: `{hist.get('monthly_cycles_observed', 'MISSING')}`",
        "",
    ]
    if args.probe_json:
        lines.extend(
            [
                "## Optional — 16-state MASTER_PROBE coverage",
                f"- path: `{args.probe_json.as_posix()}`",
                f"- states_with_audit: `{cov.get('states_with_audit', 'MISSING')}` / `{cov.get('states_total', 16)}`",
                "",
            ]
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
