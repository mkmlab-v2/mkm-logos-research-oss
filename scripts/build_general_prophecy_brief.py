#!/usr/bin/env python3
"""Build a short Markdown brief from general_prophecy registry JSON (B rail).

Reads Layer 1 forecasts and lists resolution state; does not pull Layer 3 text.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_latest.json"
DEFAULT_OUT = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_brief_latest.md"
DEFAULT_BRIER_EVAL = ROOT / "docs" / "final" / "artifacts" / "general_prophecy_brier_eval_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _brief(doc: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("# General Prophecy Brief (B rail)")
    lines.append("")
    lines.append(f"- generated_at_utc: {_utc_now()} (brief build time)")
    lines.append(f"- registry schema: `{doc.get('schema')}`")
    lines.append(f"- research_rail: `{doc.get('research_rail')}`")
    lines.append("")
    if DEFAULT_BRIER_EVAL.is_file():
        bdoc = json.loads(DEFAULT_BRIER_EVAL.read_text(encoding="utf-8"))
        if bdoc.get("schema") == "general_prophecy_brier_eval_v1":
            m = bdoc.get("metrics") or {}
            lines.append("## Brier evaluation (latest)")
            lines.append("")
            lines.append(f"- **mean_brier_score:** `{m.get('mean_brier_score')}`")
            lines.append(f"- **n_evaluated:** `{m.get('n_evaluated')}`")
            lines.append(f"- **eval_generated_at_utc:** `{bdoc.get('generated_at_utc')}`")
            lines.append("")
    for q in doc.get("questions") or []:
        if not isinstance(q, dict):
            continue
        qid = q.get("question_id", "?")
        lines.append(f"## {qid}")
        lines.append("")
        lines.append(q.get("question_text", "").strip())
        lines.append("")
        fc = q.get("forecasts") or []
        if isinstance(fc, list) and fc:
            last = fc[-1]
            p = last.get("probability_0_1")
            sk = last.get("source_kind")
            lines.append(f"- **Latest forecast:** p={p} source_kind={sk}")
        else:
            lines.append("- **Latest forecast:** (none)")
        res = q.get("resolution") or {}
        lines.append(f"- **Resolution:** `{res.get('status', 'unknown')}`")
        if res.get("outcome_binary") is not None:
            lines.append(f"- **outcome_binary:** `{res.get('outcome_binary')}`")
        ref = q.get("layer3_interpretation_ref")
        if ref:
            lines.append(f"- **Layer3 ref:** `{ref}`")
        lines.append("")
    lines.append("---\n*Creative-Lock / observation only. Not a production trading signal.*\n")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", "-i", type=Path, default=DEFAULT_IN)
    ap.add_argument("--output", "-o", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    ns = ap.parse_args()
    if not ns.input.is_file():
        print(f"missing {ns.input}", file=sys.stderr)
        return 2
    doc = _load(ns.input)
    if doc.get("schema") != "general_prophecy_registry_v1":
        print("input must be general_prophecy_registry_v1", file=sys.stderr)
        return 2
    md = _brief(doc)
    if ns.stdout_only:
        sys.stdout.write(md)
        return 0
    ns.output.parent.mkdir(parents=True, exist_ok=True)
    ns.output.write_text(md, encoding="utf-8")
    print(str(ns.output.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
