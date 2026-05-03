#!/usr/bin/env python3
"""Split pending Athena request packets into prompt-wise batch markdown files."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
PENDING_JSONL = ART / "vibe_runs_raw" / "athena_pending_requests_latest.jsonl"
OUT_DIR = ART / "vibe_runs_raw" / "athena_pending_batches"
INDEX_MD = OUT_DIR / "INDEX.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def main() -> int:
    rows = read_jsonl(PENDING_JSONL)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row.get("prompt_id", "unknown"))].append(row)

    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    written_files: list[tuple[str, int]] = []

    for prompt_id, items in sorted(grouped.items()):
        items = sorted(items, key=lambda x: int(x.get("run_index", 0)))
        out = OUT_DIR / f"{prompt_id}_batch.md"
        lines = [
            f"# Athena Pending Batch - {prompt_id}",
            "",
            f"- Generated (UTC): {now}",
            f"- Pending count: {len(items)}",
            "",
            "## Batch Instructions",
            "- For each run index, produce one response and save to target file.",
            "- Required fields:",
            "  - Final Action: HOLD|REDUCE|WATCH",
            "  - Confidence: 0.00~1.00",
            "  - Risk Flags: [comma-separated tags]",
            "  - Rationale: <= 3 lines",
            "",
        ]
        for item in items:
            lines.extend(
                [
                    f"## Run {int(item.get('run_index', 0)):02d}",
                    f"- Target file: `{item.get('target_raw_output_file')}`",
                    "",
                    "### Request",
                    item.get("request_text", ""),
                    "",
                ]
            )
        out.write_text("\n".join(lines), encoding="utf-8")
        written_files.append((out.name, len(items)))

    index_lines = [
        "# Athena Pending Batches Index",
        "",
        f"- Generated (UTC): {now}",
        f"- Total pending requests: {len(rows)}",
        "",
        "## Batch Files",
    ]
    for name, count in written_files:
        index_lines.append(f"- `{name}`: {count}")
    index_lines.append("")
    INDEX_MD.write_text("\n".join(index_lines), encoding="utf-8")

    print(f"written_dir: {OUT_DIR}")
    print(f"batch_files: {len(written_files)}")
    print(f"total_pending: {len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

