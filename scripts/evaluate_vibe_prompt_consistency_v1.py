#!/usr/bin/env python3
"""Evaluate decision consistency from Vibe prompt run JSONL."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"
RUNS_JSONL = ART / "vibe_runs_raw" / "vibe_prompt_runs_latest.jsonl"
OUT_JSON = ART / "vibe_prompt_consistency_report_latest.json"
OUT_MD = ART / "vibe_prompt_consistency_report_latest.md"


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    if not RUNS_JSONL.is_file():
        raise FileNotFoundError(f"missing runs file: {RUNS_JSONL}")

    rows = load_rows(RUNS_JSONL)
    by_prompt: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_prompt[str(row.get("prompt_id"))].append(row)

    prompt_reports = []
    for prompt_id, items in sorted(by_prompt.items()):
        decisions = [str(i.get("decision")) for i in items if i.get("decision") in {"HOLD", "REDUCE", "WATCH"}]
        total = len(items)
        valid = len(decisions)
        if valid == 0:
            dominant = None
            ratio = 0.0
            counts: dict[str, int] = {}
        else:
            counter = Counter(decisions)
            dominant, dominant_count = counter.most_common(1)[0]
            ratio = dominant_count / valid
            counts = dict(counter)
        prompt_reports.append(
            {
                "prompt_id": prompt_id,
                "total_rows": total,
                "valid_decision_rows": valid,
                "dominant_decision": dominant,
                "decision_counts": counts,
                "decision_consistency_ratio": round(ratio, 6),
            }
        )

    overall_valid = sum(p["valid_decision_rows"] for p in prompt_reports)
    overall_weighted = (
        sum(p["decision_consistency_ratio"] * p["valid_decision_rows"] for p in prompt_reports) / overall_valid
        if overall_valid > 0
        else 0.0
    )

    report = {
        "schema": "vibe_prompt_consistency_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "scope": "research_only",
        "runs_file": str(RUNS_JSONL).replace("\\", "/"),
        "prompt_reports": prompt_reports,
        "overall": {
            "prompt_count": len(prompt_reports),
            "valid_decision_rows": overall_valid,
            "overall_weighted_consistency_ratio": round(overall_weighted, 6),
        },
    }
    OUT_JSON.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    md_lines = [
        "# Vibe Prompt Consistency Report (Latest)",
        "",
        f"- Generated (UTC): {report['generated_at_utc']}",
        f"- Valid decision rows: {report['overall']['valid_decision_rows']}",
        f"- Overall weighted consistency ratio: {report['overall']['overall_weighted_consistency_ratio']}",
        "",
        "## Prompt-Level Ratios",
    ]
    for p in prompt_reports:
        md_lines.append(
            f"- {p['prompt_id']}: ratio={p['decision_consistency_ratio']} "
            f"(dominant={p['dominant_decision']}, valid={p['valid_decision_rows']}/{p['total_rows']})"
        )
    md_lines.append("")
    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(f"written: {OUT_JSON}")
    print(f"written: {OUT_MD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

