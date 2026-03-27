#!/usr/bin/env python3
"""Validate training JSONL quality and deduplicate statistics."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = WORKSPACE_ROOT / "reports" / "constitution" / "master_codebook_training_multidomain_1000.jsonl"
DEFAULT_JSON_OUT = WORKSPACE_ROOT / "reports" / "constitution" / "master_codebook_training_quality_latest.json"
DEFAULT_MD_OUT = WORKSPACE_ROOT / "reports" / "constitution" / "master_codebook_training_quality_latest.md"


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _pair_hash(prompt: str, response: str) -> str:
    payload = f"{prompt}\n<SEP>\n{response}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Validate training JSONL quality")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_INPUT), help="Input JSONL path")
    ap.add_argument("--json-out", dest="json_out", default=str(DEFAULT_JSON_OUT), help="Output quality JSON path")
    ap.add_argument("--md-out", dest="md_out", default=str(DEFAULT_MD_OUT), help="Output quality Markdown path")
    ap.add_argument("--min-prompt-len", type=int, default=8, help="Minimum prompt length")
    ap.add_argument("--min-response-len", type=int, default=2, help="Minimum response length")
    args = ap.parse_args()

    input_path = _as_abs(args.input_path)
    json_out = _as_abs(args.json_out)
    md_out = _as_abs(args.md_out)
    if not input_path.is_file():
        print(f"❌ input not found: {input_path}")
        return 1

    total = 0
    duplicate_pairs = 0
    missing_required = 0
    short_prompt = 0
    short_response = 0
    failed_quality = 0
    unique_hashes: set[str] = set()
    domain_counter: Counter[str] = Counter()
    split_counter: Counter[str] = Counter()

    required_fields = {
        "training_id",
        "lookup_id_ref",
        "domain",
        "input_key",
        "prompt",
        "response",
        "split",
        "quality_gate_passed",
    }

    with input_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            total += 1
            row: dict[str, Any] = json.loads(line)

            if not required_fields.issubset(set(row.keys())):
                missing_required += 1
                continue

            prompt = str(row.get("prompt", ""))
            response = str(row.get("response", ""))
            split_counter[str(row.get("split", "unknown"))] += 1
            domain_counter[str(row.get("domain", "unknown"))] += 1

            if len(prompt.strip()) < args.min_prompt_len:
                short_prompt += 1
            if len(response.strip()) < args.min_response_len:
                short_response += 1
            if row.get("quality_gate_passed") is not True:
                failed_quality += 1

            ph = _pair_hash(prompt.strip(), response.strip())
            if ph in unique_hashes:
                duplicate_pairs += 1
            else:
                unique_hashes.add(ph)

    report = {
        "input": str(input_path),
        "total_records": total,
        "unique_prompt_response_pairs": len(unique_hashes),
        "duplicate_prompt_response_pairs": duplicate_pairs,
        "missing_required_fields": missing_required,
        "short_prompt_count": short_prompt,
        "short_response_count": short_response,
        "quality_gate_failed_count": failed_quality,
        "domain_distribution": dict(domain_counter),
        "split_distribution": dict(split_counter),
        "pass": all(
            [
                total > 0,
                duplicate_pairs == 0,
                missing_required == 0,
                short_prompt == 0,
                short_response == 0,
                failed_quality == 0,
            ]
        ),
    }

    json_out.parent.mkdir(parents=True, exist_ok=True)
    with json_out.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")

    md_lines = [
        "# Training JSONL Quality Report",
        "",
        f"- input: `{input_path}`",
        f"- total_records: **{total}**",
        f"- unique_prompt_response_pairs: **{len(unique_hashes)}**",
        f"- duplicate_prompt_response_pairs: **{duplicate_pairs}**",
        f"- missing_required_fields: **{missing_required}**",
        f"- short_prompt_count: **{short_prompt}**",
        f"- short_response_count: **{short_response}**",
        f"- quality_gate_failed_count: **{failed_quality}**",
        f"- pass: **{report['pass']}**",
        "",
        "## Domain Distribution",
    ]
    for k, v in domain_counter.items():
        md_lines.append(f"- {k}: {v}")

    md_lines.append("")
    md_lines.append("## Split Distribution")
    for k, v in split_counter.items():
        md_lines.append(f"- {k}: {v}")

    with md_out.open("w", encoding="utf-8") as f:
        f.write("\n".join(md_lines) + "\n")

    status = "✅" if report["pass"] else "❌"
    print(f"{status} quality report generated")
    print(f"json: {json_out.resolve()}")
    print(f"md: {md_out.resolve()}")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
