#!/usr/bin/env python3
"""Check expected raw output coverage for Vibe prompt runs."""

from __future__ import annotations

import json
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
RUNS = ART / "vibe_runs_raw" / "vibe_prompt_runs_latest.jsonl"
RAW_DIR = ART / "vibe_runs_raw" / "athena_raw_outputs"
OUT_JSON = ART / "vibe_runs_raw" / "vibe_raw_coverage_latest.json"
OUT_MD = ART / "vibe_runs_raw" / "vibe_raw_coverage_latest.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def expected_filename(prompt_id: str, run_index: int) -> str:
    return f"{prompt_id}_run_{run_index:02d}.md"


def is_filled_output(path: Path) -> bool:
    text = path.read_text(encoding="utf-8", errors="ignore")
    upper = text.upper()
    # Slot template marker means "not filled yet"
    if "FINAL ACTION: HOLD|REDUCE|WATCH" in upper:
        return False
    # Consider filled when one of valid actions is present
    return any(token in upper for token in ("HOLD", "REDUCE", "WATCH"))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fail-below-filled", type=float, default=None)
    args = parser.parse_args()

    rows = read_jsonl(RUNS)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    missing: list[str] = []
    unfilled: list[str] = []
    existing = 0
    filled = 0
    for row in rows:
        prompt_id = str(row.get("prompt_id"))
        run_index = int(row.get("run_index"))
        fname = expected_filename(prompt_id, run_index)
        fpath = RAW_DIR / fname
        if fpath.exists():
            existing += 1
            if is_filled_output(fpath):
                filled += 1
            else:
                unfilled.append(fname)
        else:
            missing.append(fname)

    total = len(rows)
    coverage = (existing / total) if total > 0 else 0.0
    filled_ratio = (filled / total) if total > 0 else 0.0
    status = "ok" if filled_ratio >= 0.95 else "needs_attention"

    report = {
        "schema": "vibe_raw_output_coverage_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "research_only",
        "runs_file": str(RUNS).replace("\\", "/"),
        "raw_dir": str(RAW_DIR).replace("\\", "/"),
        "total_expected": total,
        "existing_raw_files": existing,
        "filled_raw_files": filled,
        "coverage_ratio": round(coverage, 6),
        "filled_coverage_ratio": round(filled_ratio, 6),
        "status": status,
        "missing_files": missing[:200],
        "unfilled_files": unfilled[:200],
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# Vibe Raw Output Coverage (Latest)",
        "",
        f"- Generated (UTC): {report['generated_at_utc']}",
        f"- Expected: {total}",
        f"- Existing: {existing}",
        f"- Coverage ratio: {report['coverage_ratio']}",
        f"- Filled: {filled}",
        f"- Filled coverage ratio: {report['filled_coverage_ratio']}",
        f"- Status: {status}",
        "",
    ]
    if missing:
        md.append("## Missing (first 50)")
        for name in missing[:50]:
            md.append(f"- {name}")
        md.append("")
    if unfilled:
        md.append("## Unfilled Template Slots (first 50)")
        for name in unfilled[:50]:
            md.append(f"- {name}")
        md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")
    print(f"written: {OUT_JSON}")
    print(f"written: {OUT_MD}")
    print(f"coverage_ratio: {report['coverage_ratio']}")
    print(f"filled_coverage_ratio: {report['filled_coverage_ratio']}")
    if args.fail_below_filled is not None and filled_ratio < float(args.fail_below_filled):
        print(
            f"gate_fail: filled_coverage_ratio {filled_ratio:.6f} < required {float(args.fail_below_filled):.6f}"
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

