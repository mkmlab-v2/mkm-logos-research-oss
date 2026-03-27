#!/usr/bin/env python3
"""Generate count/split/domain distribution report from training JSONL."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = WORKSPACE_ROOT / "reports" / "constitution" / "master_codebook_training_phaseA_200.jsonl"
DEFAULT_JSON_OUT = WORKSPACE_ROOT / "reports" / "constitution" / "master_codebook_training_distribution_latest.json"
DEFAULT_MD_OUT = WORKSPACE_ROOT / "reports" / "constitution" / "master_codebook_training_distribution_latest.md"


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _pct(part: int, whole: int) -> float:
    if whole <= 0:
        return 0.0
    return round((part / whole) * 100.0, 2)


def main() -> int:
    ap = argparse.ArgumentParser(description="Report distribution from training JSONL")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_INPUT), help="Input JSONL path")
    ap.add_argument("--json-out", dest="json_out", default=str(DEFAULT_JSON_OUT), help="Output JSON report path")
    ap.add_argument("--md-out", dest="md_out", default=str(DEFAULT_MD_OUT), help="Output Markdown report path")
    args = ap.parse_args()

    input_path = _as_abs(args.input_path)
    json_out = _as_abs(args.json_out)
    md_out = _as_abs(args.md_out)

    if not input_path.is_file():
        print(f"❌ input not found: {input_path}")
        return 1

    split_counter: Counter[str] = Counter()
    domain_counter: Counter[str] = Counter()
    input_key_counter: Counter[str] = Counter()
    quality_counter: Counter[str] = Counter()
    total = 0

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            row: dict[str, Any] = json.loads(line)
            total += 1
            split_counter[str(row.get("split", "unknown"))] += 1
            domain_counter[str(row.get("domain", "unknown"))] += 1
            input_key_counter[str(row.get("input_key", "unknown"))] += 1
            quality_counter[str(row.get("quality_gate_passed", "unknown"))] += 1

    report = {
        "input": str(input_path),
        "total_records": total,
        "split_distribution": dict(split_counter),
        "domain_distribution": dict(domain_counter),
        "input_key_distribution": dict(input_key_counter),
        "quality_distribution": dict(quality_counter),
        "single_domain_ratio_percent": _pct(max(domain_counter.values()) if domain_counter else 0, total),
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    with json_out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    md_lines = [
        "# Training JSONL Distribution Report",
        "",
        f"- input: `{input_path}`",
        f"- total_records: **{total}**",
        f"- single_domain_ratio_percent: **{report['single_domain_ratio_percent']}%**",
        "",
        "## Split Distribution",
    ]
    for k, v in split_counter.items():
        md_lines.append(f"- {k}: {v} ({_pct(v, total)}%)")

    md_lines.append("")
    md_lines.append("## Domain Distribution")
    for k, v in domain_counter.items():
        md_lines.append(f"- {k}: {v} ({_pct(v, total)}%)")

    md_lines.append("")
    md_lines.append("## Input Key Distribution")
    for k, v in input_key_counter.items():
        md_lines.append(f"- {k}: {v} ({_pct(v, total)}%)")

    md_lines.append("")
    md_lines.append("## Quality Distribution")
    for k, v in quality_counter.items():
        md_lines.append(f"- {k}: {v} ({_pct(v, total)}%)")

    with md_out.open("w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    print(f"✅ report generated")
    print(f"json: {json_out.resolve()}")
    print(f"md: {md_out.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
