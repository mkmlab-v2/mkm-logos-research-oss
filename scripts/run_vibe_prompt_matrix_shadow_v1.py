#!/usr/bin/env python3
"""Generate Vibe B-Track prompt run matrix (research-only shadow loop)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
PROMPTS_MD = ART / "vibe_prompt_set_v1.md"
RUNS_DIR = ART / "vibe_runs_raw"
RUNS_JSONL = RUNS_DIR / "vibe_prompt_runs_latest.jsonl"
META_JSON = RUNS_DIR / "vibe_prompt_runs_meta_latest.json"


def parse_prompts(md_text: str) -> list[dict[str, str]]:
    prompts: list[dict[str, str]] = []
    chunks = re.split(r"^## Prompt\s+\d+\s+-\s+", md_text, flags=re.MULTILINE)
    headers = re.findall(r"^## Prompt\s+\d+\s+-\s+(.+)$", md_text, flags=re.MULTILINE)
    if not headers:
        return prompts
    for idx, title in enumerate(headers, start=1):
        body = chunks[idx] if idx < len(chunks) else ""
        prompt_id = f"prompt_{idx:02d}"
        prompts.append(
            {
                "prompt_id": prompt_id,
                "title": title.strip(),
                "body": body.strip(),
            }
        )
    return prompts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs-per-prompt", type=int, default=10)
    parser.add_argument(
        "--simulate-decision",
        type=str,
        default="",
        help="Optional fixed decision (HOLD/REDUCE/WATCH) for dry-run simulation",
    )
    args = parser.parse_args()

    if not PROMPTS_MD.is_file():
        raise FileNotFoundError(f"missing prompt file: {PROMPTS_MD}")

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    prompts = parse_prompts(PROMPTS_MD.read_text(encoding="utf-8"))
    if not prompts:
        raise RuntimeError("no prompts parsed from vibe_prompt_set_v1.md")

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    with RUNS_JSONL.open("w", encoding="utf-8") as f:
        for p in prompts:
            for run_idx in range(1, args.runs_per_prompt + 1):
                row = {
                    "schema": "vibe_prompt_run_row_v1",
                    "generated_at_utc": now,
                    "scope": "research_only",
                    "track_guardrail": "no_auto_bridge_to_track_a",
                    "prompt_id": p["prompt_id"],
                    "prompt_title": p["title"],
                    "run_index": run_idx,
                    "status": "simulated" if args.simulate_decision else "pending_model_output",
                    "decision": args.simulate_decision or None,
                    "confidence": None,
                    "rationale_short": None,
                    "risk_flags": [],
                    "raw_output_path": None,
                }
                f.write(json.dumps(row, ensure_ascii=False) + "\n")

    meta = {
        "schema": "vibe_prompt_runs_meta_v1",
        "generated_at_utc": now,
        "prompt_file": str(PROMPTS_MD).replace("\\", "/"),
        "runs_file": str(RUNS_JSONL).replace("\\", "/"),
        "runs_per_prompt": args.runs_per_prompt,
        "prompt_count": len(prompts),
        "total_rows": len(prompts) * args.runs_per_prompt,
        "simulate_decision": args.simulate_decision or None,
    }
    META_JSON.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"written: {RUNS_JSONL}")
    print(f"written: {META_JSON}")
    print(f"rows: {meta['total_rows']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

