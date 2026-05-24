#!/usr/bin/env python3
"""M16a: Operator Markdown brief from wire+gloss session report (research_only)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_GLOSS = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_gloss_session_report_v1_latest.json"
DEFAULT_MD = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_ops_brief_v1_latest.md"
DEFAULT_META = ROOT / "docs/final/artifacts/mkm_inter_agent_wire_session_ops_brief_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def render_ops_brief_md(report: dict[str, Any]) -> str:
    lines = [
        "# MKM inter-agent wire session — operator brief",
        "",
        f"- Generated (UTC): {report.get('generated_at_utc', _utc())}",
        "- Classification: INTERNAL · `research_only` · B-track",
        "- Gloss source: lexicon `normalized_form` lookup on `atom_id_sequence` (not L1 lossless decode)",
        "",
        report.get("boundary_ack", ""),
        "",
    ]
    summary = report.get("scenario_summary") or {}
    if not summary:
        lines.append("_No scenario data in gloss report._")
        return "\n".join(lines) + "\n"

    lines.append("## Scenario summary")
    lines.append("")
    lines.append("| Scenario | Turns | Avg atoms | Empty turns | Gloss preview (turn 1) |")
    lines.append("| --- | ---: | ---: | ---: | --- |")
    for scenario, row in summary.items():
        lines.append(
            f"| {scenario} | {row.get('turn_count', 0)} | {row.get('avg_atom_id_count', 0)} | "
            f"{row.get('empty_turn_count', 0)} | {row.get('gloss_preview_turn_1', '')} |"
        )
    lines.append("")

    turns_by = report.get("turns_by_scenario") or {}
    for scenario, turns in turns_by.items():
        lines.append(f"## {scenario}")
        lines.append("")
        for t in turns:
            turn_n = t.get("turn")
            frm = t.get("from_agent", "?")
            to = t.get("to_agent", "?")
            gloss = t.get("gloss_text") or "(empty lexicon gloss)"
            atoms = t.get("atom_id_count", 0)
            env_b = t.get("envelope_utf8_byte_len", 0)
            wire_b = t.get("wire_byte_len", 0)
            lines.append(f"### Turn {turn_n} — {frm} → {to}")
            lines.append("")
            lines.append(f"- Envelope UTF-8: **{env_b}** B · wire payload: **{wire_b}** B · atoms: **{atoms}**")
            lines.append(f"- **Gloss:** {gloss}")
            if t.get("empty_lexicon_turn"):
                lines.append("- _Note: empty or near-empty lexicon mapping (e.g. Korean health lines)._")
            lines.append("")
    lines.append("---")
    lines.append("_Not production SLA, Track A, or live trading. RQ-019 research lane only._")
    return "\n".join(lines) + "\n"


def build_brief(
    *,
    gloss_report_path: Path = DEFAULT_GLOSS,
    run_gloss_if_missing: bool = True,
) -> dict[str, Any]:
    if not gloss_report_path.is_file():
        if not run_gloss_if_missing:
            return {"ok": False, "error": "gloss_report_missing"}
        from scripts.build_mkm_inter_agent_wire_gloss_session_report_v1 import build_report

        built = build_report(run_batch_if_missing=True)
        if not built.get("ok"):
            return {"ok": False, "error": "gloss_report_build_failed"}
        gloss_report_path = DEFAULT_GLOSS

    report = json.loads(gloss_report_path.read_text(encoding="utf-8"))
    if not report.get("ok"):
        return {"ok": False, "error": "gloss_report_not_ok"}

    md = render_ops_brief_md(report)
    scenario_count = len(report.get("scenario_summary") or {})
    return {
        "ok": scenario_count >= 1,
        "schema": "mkm_inter_agent_wire_session_ops_brief_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "gloss_report": gloss_report_path.relative_to(ROOT).as_posix(),
        "scenario_count": scenario_count,
        "markdown_char_len": len(md),
        "markdown": md,
        "boundary_ack": report.get("boundary_ack"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gloss-report", type=Path, default=DEFAULT_GLOSS)
    ap.add_argument("--out-md", type=Path, default=DEFAULT_MD)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_META)
    ap.add_argument("--no-run-gloss", action="store_true")
    args = ap.parse_args()

    doc = build_brief(gloss_report_path=args.gloss_report, run_gloss_if_missing=not args.no_run_gloss)
    if not doc.get("ok"):
        print(json.dumps(doc, ensure_ascii=False))
        return 2

    md = str(doc.pop("markdown", ""))
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "md": str(args.out_md), "meta": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
