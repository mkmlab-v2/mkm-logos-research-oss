#!/usr/bin/env python3
"""Build pending request packets for unfilled Athena raw output slots."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
RUNS_JSONL = ART / "vibe_runs_raw" / "vibe_prompt_runs_latest.jsonl"
RAW_DIR = ART / "vibe_runs_raw" / "athena_raw_outputs"
PROMPTS_MD = ART / "vibe_prompt_set_v1.md"

OUT_JSONL = ART / "vibe_runs_raw" / "athena_pending_requests_latest.jsonl"
OUT_MD = ART / "vibe_runs_raw" / "athena_pending_requests_latest.md"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def parse_prompts(md_text: str) -> dict[str, str]:
    prompt_map: dict[str, str] = {}
    chunks = re.split(r"^## Prompt\s+\d+\s+-\s+", md_text, flags=re.MULTILINE)
    headers = re.findall(r"^## Prompt\s+\d+\s+-\s+(.+)$", md_text, flags=re.MULTILINE)
    for idx, title in enumerate(headers, start=1):
        body = chunks[idx] if idx < len(chunks) else ""
        pid = f"prompt_{idx:02d}"
        prompt_map[pid] = f"{title.strip()}\n\n{body.strip()}"
    return prompt_map


def is_filled_text(text: str) -> bool:
    up = text.upper()
    if "FINAL ACTION: HOLD|REDUCE|WATCH" in up:
        return False
    return any(x in up for x in ("HOLD", "REDUCE", "WATCH"))


def main() -> int:
    runs = read_jsonl(RUNS_JSONL)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    prompt_map = parse_prompts(PROMPTS_MD.read_text(encoding="utf-8")) if PROMPTS_MD.is_file() else {}

    pending: list[dict[str, Any]] = []
    for row in runs:
        prompt_id = str(row.get("prompt_id"))
        run_idx = int(row.get("run_index"))
        fname = f"{prompt_id}_run_{run_idx:02d}.md"
        fpath = RAW_DIR / fname
        if not fpath.exists():
            is_filled = False
        else:
            is_filled = is_filled_text(fpath.read_text(encoding="utf-8", errors="ignore"))
        if is_filled:
            continue
        packet = {
            "schema": "athena_pending_request_packet_v1",
            "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "prompt_id": prompt_id,
            "run_index": run_idx,
            "target_raw_output_file": str(fpath).replace("\\", "/"),
            "request_text": (
                "Return exactly these fields:\n"
                "Final Action: HOLD|REDUCE|WATCH\n"
                "Confidence: 0.00~1.00\n"
                "Risk Flags: [comma-separated tags]\n"
                "Rationale: <= 3 lines\n\n"
                f"Prompt Context:\n{prompt_map.get(prompt_id, '(missing prompt context)')}"
            ),
        }
        pending.append(packet)

    with OUT_JSONL.open("w", encoding="utf-8") as f:
        for p in pending:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")

    md = [
        "# Athena Pending Request Packets (Latest)",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}",
        f"- Pending slots: {len(pending)}",
        "",
        "## Pending Targets (first 50)",
    ]
    for p in pending[:50]:
        md.append(f"- {p['prompt_id']} run={p['run_index']:02d} -> `{p['target_raw_output_file']}`")
    md.append("")
    md.append("## Copy-Paste Request Template")
    md.append(
        "Return exactly these fields:\n"
        "Final Action: HOLD|REDUCE|WATCH\n"
        "Confidence: 0.00~1.00\n"
        "Risk Flags: [comma-separated tags]\n"
        "Rationale: <= 3 lines"
    )
    md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    print(f"written: {OUT_JSONL}")
    print(f"written: {OUT_MD}")
    print(f"pending_slots: {len(pending)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

