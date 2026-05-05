#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def _load_json(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build falsification fail-boundary report from sensitivity grid.")
    ap.add_argument(
        "--sensitivity-json",
        default="docs/final/artifacts/two_track_falsification_sensitivity_latest.json",
    )
    ap.add_argument(
        "--suite-json",
        default="docs/final/artifacts/two_track_falsification_suite_latest.json",
    )
    ap.add_argument(
        "--output-json",
        default="docs/final/artifacts/two_track_falsification_boundary_report_latest.json",
    )
    args = ap.parse_args()

    sensitivity_path = _resolve(args.sensitivity_json)
    suite_path = _resolve(args.suite_json)
    out_path = _resolve(args.output_json)
    if not sensitivity_path.is_file():
        raise SystemExit(f"missing sensitivity json: {sensitivity_path}")
    if not suite_path.is_file():
        raise SystemExit(f"missing suite json: {suite_path}")

    sensitivity = _load_json(sensitivity_path)
    suite = _load_json(suite_path)
    grid = sensitivity.get("grid") if isinstance(sensitivity.get("grid"), list) else []
    valid_rows = [r for r in grid if isinstance(r, dict)]
    pass_rows = [r for r in valid_rows if str(r.get("suite_status")) == "pass"]
    non_pass_rows = [r for r in valid_rows if str(r.get("suite_status")) != "pass"]

    first_non_pass = non_pass_rows[0] if non_pass_rows else None
    max_safe_survivor = max((int(r.get("min_survivor_count", 0) or 0) for r in pass_rows), default=0)
    min_break_survivor = min((int(r.get("min_survivor_count", 0) or 0) for r in non_pass_rows), default=None)
    max_safe_ci = max((float(r.get("min_ci_low_defense_contrib", 0.0) or 0.0) for r in pass_rows), default=0.0)

    out = {
        "schema": "two_track_falsification_boundary_report_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "source": {"sensitivity_json": str(sensitivity_path), "suite_json": str(suite_path)},
        "current_suite_snapshot": {
            "pass_count": int(suite.get("pass_count", 0) or 0),
            "total_checks": int(suite.get("total_checks", 0) or 0),
            "suite_status": str(suite.get("suite_status", "unknown")),
        },
        "boundary_summary": {
            "grid_rows": len(valid_rows),
            "pass_rows": len(pass_rows),
            "non_pass_rows": len(non_pass_rows),
            "max_safe_min_survivor_count": max_safe_survivor,
            "max_safe_min_ci_low_defense_contrib": max_safe_ci,
            "first_non_pass_row": first_non_pass,
            "min_break_min_survivor_count": min_break_survivor,
        },
        "operator_note": (
            "Use first_non_pass_row as fail-scenario reference in reviewer Q&A and risk boundary disclosure."
        ),
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

