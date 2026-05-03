#!/usr/bin/env python3
"""Create expected Athena raw output slot files for prompt matrix."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "docs" / "final" / "artifacts" / "vibe_runs_raw" / "athena_raw_outputs"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-count", type=int, default=4)
    parser.add_argument("--runs-per-prompt", type=int, default=10)
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    created = 0
    touched = 0
    for p in range(1, args.prompt_count + 1):
        for r in range(1, args.runs_per_prompt + 1):
            name = f"prompt_{p:02d}_run_{r:02d}.md"
            path = OUT_DIR / name
            if path.exists():
                touched += 1
                continue
            path.write_text(
                "\n".join(
                    [
                        f"# {name}",
                        "",
                        "Final Action: HOLD|REDUCE|WATCH",
                        "Confidence: 0.00",
                        "Risk Flags: []",
                        "Rationale: ...",
                        "",
                    ]
                ),
                encoding="utf-8",
            )
            created += 1

    print(f"slot_dir: {OUT_DIR}")
    print(f"created_files: {created}")
    print(f"existing_files_untouched: {touched}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

