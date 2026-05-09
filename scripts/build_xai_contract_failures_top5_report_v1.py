#!/usr/bin/env python3
"""Build Top5 failure report + action queue from xai_contract_failures_latest.json."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "xai_contract_failures_latest.json"
DEFAULT_OUT_JSON = ROOT / "docs" / "final" / "artifacts" / "xai_contract_failures_top5_latest.json"
DEFAULT_OUT_MD = ROOT / "docs" / "final" / "artifacts" / "xai_contract_failures_top5_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _missing_fields(checks: dict[str, Any]) -> list[str]:
    mapping = {
        "has_conclusion_one_line": "conclusion_one_line",
        "has_evidence_3plus": "evidence_3plus",
        "has_limitation_one": "limitation_one",
        "has_action_guide_one": "action_guide_one",
        "has_claim_type_labels": "claim_type_labels",
        "has_confidence_0_1": "confidence_0_1",
    }
    out: list[str] = []
    for k, label in mapping.items():
        if checks.get(k) is False:
            out.append(label)
    return out


def _priority_score(row: dict[str, Any]) -> int:
    pri = str(row.get("priority") or "").lower()
    base = {"high": 3, "medium": 2, "low": 1}.get(pri, 1)
    checks = row.get("checks") if isinstance(row.get("checks"), dict) else {}
    miss = len(_missing_fields(checks))
    return base * 10 + miss


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT_JSON)
    ap.add_argument("--output-md", type=Path, default=DEFAULT_OUT_MD)
    ns = ap.parse_args()

    doc = _load(ns.input)
    rows = doc.get("rows") if isinstance(doc.get("rows"), list) else []
    fail_rows = [r for r in rows if isinstance(r, dict)]
    fail_rows = sorted(fail_rows, key=_priority_score, reverse=True)
    top5 = fail_rows[:5]

    action_queue: list[dict[str, Any]] = []
    for i, row in enumerate(top5, start=1):
        checks = row.get("checks") if isinstance(row.get("checks"), dict) else {}
        action_queue.append(
            {
                "rank": i,
                "question_id": row.get("question_id"),
                "domain_tag": row.get("domain_tag"),
                "priority": row.get("priority"),
                "missing_fields": _missing_fields(checks),
                "recommended_action": "Fill missing contract fields and re-run gate.",
            }
        )

    out = {
        "schema": "xai_contract_failures_top5_v1",
        "generated_at_utc": _utc_now(),
        "input_path": str(ns.input.resolve()).replace("\\", "/"),
        "metrics": {
            "fail_count": len(fail_rows),
            "top5_count": len(top5),
        },
        "top5": top5,
        "action_queue": action_queue,
    }
    ns.output_json.parent.mkdir(parents=True, exist_ok=True)
    ns.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# XAI Contract Failures Top5",
        "",
        f"- generated_at_utc: `{out['generated_at_utc']}`",
        f"- fail_count: `{out['metrics']['fail_count']}`",
        f"- top5_count: `{out['metrics']['top5_count']}`",
        "",
        "## Action Queue",
    ]
    if not action_queue:
        md_lines.append("- No failures. Queue is empty.")
    else:
        for item in action_queue:
            miss = ", ".join(item["missing_fields"]) if item["missing_fields"] else "none"
            md_lines.append(
                f"- `{item['rank']}. {item['question_id']}` ({item['priority']}/{item['domain_tag']}): missing `{miss}` -> {item['recommended_action']}"
            )
    ns.output_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    print(str(ns.output_json.resolve()))
    print(str(ns.output_md.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
