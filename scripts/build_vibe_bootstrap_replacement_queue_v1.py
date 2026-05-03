#!/usr/bin/env python3
"""Build replacement queue for bootstrap-filled Athena raw outputs."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "docs" / "final" / "artifacts" / "vibe_runs_raw" / "athena_raw_outputs"
LEGACY_BOOTSTRAP_TAG = "auto_fill_codex_bootstrap"
RESEARCH_STUB_TAG = "research_stub_evidence_v1"

OUT_JSONL = ROOT / "docs" / "final" / "artifacts" / "vibe_runs_raw" / "vibe_bootstrap_replacement_queue_latest.jsonl"
OUT_MD = ROOT / "docs" / "final" / "artifacts" / "vibe_runs_raw" / "vibe_bootstrap_replacement_queue_latest.md"


def parse_slot_meta(path: Path) -> tuple[str | None, int | None]:
    m = re.match(r"^(prompt_\d{2})_run_(\d+)\.(?:md|txt)$", path.name, flags=re.IGNORECASE)
    if not m:
        return None, None
    return m.group(1).lower(), int(m.group(2))


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    OUT_JSONL.parent.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for path in sorted(RAW_DIR.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in {".md", ".txt"}:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        is_legacy = LEGACY_BOOTSTRAP_TAG in text
        is_stub = RESEARCH_STUB_TAG in text
        if not (is_legacy or is_stub):
            continue
        prompt_id, run_index = parse_slot_meta(path)
        rows.append(
            {
                "schema": "vibe_bootstrap_replacement_queue_row_v1",
                "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "prompt_id": prompt_id,
                "run_index": run_index,
                "raw_output_file": str(path).replace("\\", "/"),
                "bootstrap_tag": LEGACY_BOOTSTRAP_TAG if is_legacy else RESEARCH_STUB_TAG,
                "replacement_instructions": (
                    "Overwrite this file with a real Athena response. "
                    "Keep fields: Final Action / Confidence / Risk Flags / Rationale. "
                    "Remove bootstrap/stub markers when replaced."
                ),
            }
        )

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    md = [
        "# Bootstrap Replacement Queue (Latest)",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- Queue rows: {len(rows)}",
        "",
        "## Next Steps",
        "- Replace each listed file with real Athena output.",
        "- Remove bootstrap tags after replacement.",
        "- Re-run strict loop after replacements:",
        "  - `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_vibe_daily_prophecy_evolution_loop_v1.ps1 -RunsPerPrompt 10 -StrictCoverageGate`",
        "",
        "## Queue (first 50)",
    ]
    for row in rows[:50]:
        md.append(f"- `{row['raw_output_file']}`")
    md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"written: {OUT_JSONL}")
    print(f"written: {OUT_MD}")
    print(f"queue_rows: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
