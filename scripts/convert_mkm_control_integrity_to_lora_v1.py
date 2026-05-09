#!/usr/bin/env python3
"""Convert MKM control-integrity golden set v1 to LoRA instruction/response format.

Compatibility:
- `response` for requested format.
- `output` alias for existing repo training scripts.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_IN = WORKSPACE_ROOT / "scripts" / "data" / "mkm_control_integrity_golden_set_v1_1000.jsonl"
DEFAULT_OUT = WORKSPACE_ROOT / "scripts" / "data" / "mkm_control_integrity_golden_set_v1_lora_1000.jsonl"


def _as_abs(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else (WORKSPACE_ROOT / p)


def _build_instruction(row: dict[str, Any]) -> str:
    # Keep instruction compact for LoRA while preserving safety constraints.
    header = (
        f"[domain={row.get('domain')}] "
        f"[risk={row.get('risk_level')}] "
        f"[split={row.get('split')}] "
        f"[lang={row.get('language')}]"
    )
    include = ", ".join(row.get("must_include", []))
    exclude = ", ".join(row.get("must_not_include", []))
    tags = ", ".join(row.get("policy_tags", []))
    prompt = str(row.get("prompt", "")).strip()
    context = str(row.get("context", "")).strip()
    lines = [
        header,
        f"Policy tags: {tags}",
        f"Must include: {include}",
        f"Must not include: {exclude}",
        f"Prompt: {prompt}",
    ]
    if context:
        lines.append(f"Context: {context}")
    lines.append("Respond with fact-locked and safety-aligned answer.")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description="Convert golden set v1 JSONL to LoRA instruction/response JSONL")
    ap.add_argument("--in", dest="input_path", default=str(DEFAULT_IN), help="Input golden set JSONL path")
    ap.add_argument("--out", dest="output_path", default=str(DEFAULT_OUT), help="Output LoRA JSONL path")
    args = ap.parse_args()

    input_path = _as_abs(args.input_path)
    output_path = _as_abs(args.output_path)
    if not input_path.is_file():
        print(f"input not found: {input_path}")
        return 1

    total = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with input_path.open("r", encoding="utf-8") as src, output_path.open("w", encoding="utf-8") as dst:
        for line_no, raw in enumerate(src, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                print(f"line {line_no}: invalid json: {exc}")
                return 2

            profile = row.get("scoring_profile", {})
            response_text = row.get("expected_response", "")
            converted = {
                "schema": "mkm_lora_instruction_response_v1",
                "id": row.get("sample_id"),
                "instruction": _build_instruction(row),
                "response": response_text,
                "output": response_text,
                "metadata": {
                    "split": row.get("split"),
                    "domain": row.get("domain"),
                    "risk_level": row.get("risk_level"),
                    "language": row.get("language"),
                    "policy_tags": row.get("policy_tags", []),
                    "pass_threshold": profile.get("pass_threshold"),
                },
            }
            dst.write(json.dumps(converted, ensure_ascii=False))
            dst.write("\n")
            total += 1

    print(f"rows={total}")
    print(f"out={output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
