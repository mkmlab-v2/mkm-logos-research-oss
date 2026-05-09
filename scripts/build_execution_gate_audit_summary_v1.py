from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build execution gate audit summary.")
    p.add_argument(
        "--audit-jsonl",
        default="reports/execution_gate_audit_log.jsonl",
        help="Execution gate audit log JSONL path.",
    )
    p.add_argument(
        "--output-json",
        default="reports/execution_gate_audit_summary_latest.json",
        help="Summary JSON output path.",
    )
    p.add_argument(
        "--output-md",
        default="reports/execution_gate_audit_summary_latest.md",
        help="Summary Markdown output path.",
    )
    p.add_argument(
        "--top-reasons",
        type=int,
        default=5,
        help="Top block reasons to include.",
    )
    return p.parse_args()


def read_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
            if isinstance(row, dict):
                rows.append(row)
        except json.JSONDecodeError:
            continue
    return rows


def build_summary(rows: list[dict[str, Any]], top_n: int) -> dict[str, Any]:
    total = len(rows)
    block_rows = [r for r in rows if str(r.get("decision", "")).upper() == "BLOCK"]
    allow_rows = [r for r in rows if str(r.get("decision", "")).upper() == "ALLOW"]
    reason_counter: Counter[str] = Counter()
    for row in block_rows:
        reasons = row.get("reasons", [])
        if isinstance(reasons, list):
            for r in reasons:
                reason_counter[str(r)] += 1
    top_reasons = [{"reason": k, "count": v} for k, v in reason_counter.most_common(max(top_n, 1))]
    return {
        "schema": "execution_gate_audit_summary_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_rows": total,
        "allow_count": len(allow_rows),
        "block_count": len(block_rows),
        "block_ratio": (len(block_rows) / total) if total else 0.0,
        "top_block_reasons": top_reasons,
    }


def write_outputs(summary: dict[str, Any], output_json: Path, output_md: Path) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Execution Gate Audit Summary",
        "",
        f"- generated_at_utc: `{summary['generated_at_utc']}`",
        f"- total_rows: `{summary['total_rows']}`",
        f"- allow_count: `{summary['allow_count']}`",
        f"- block_count: `{summary['block_count']}`",
        f"- block_ratio: `{summary['block_ratio']:.4f}`",
        "",
        "## Top Block Reasons",
    ]
    if summary["top_block_reasons"]:
        for item in summary["top_block_reasons"]:
            lines.append(f"- `{item['reason']}`: `{item['count']}`")
    else:
        lines.append("- none")
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    rows = read_rows(Path(args.audit_jsonl))
    summary = build_summary(rows, args.top_reasons)
    write_outputs(summary, Path(args.output_json), Path(args.output_md))
    print(f"execution_gate_audit_summary_written={args.output_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
