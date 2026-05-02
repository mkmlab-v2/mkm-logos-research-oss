#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Materialize `DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md` fields from disk SSOT JSON only.

Outputs a 1-page Markdown brief (observation / hygiene — not trading advice).
Template SSOT: projects/bitcoin-trading/ops/windows-rehearsal/DAILY_EXECUTION_INSIGHT_BRIEF_TEMPLATE.md
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FUSION = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "independent_lens_fusion_stub_latest.json"
DEFAULT_THIN = WORKSPACE_ROOT / "docs" / "final" / "artifacts" / "multilens_eval_v2_thin_report_latest.json"
DEFAULT_OUT = WORKSPACE_ROOT / "reports" / "daily_execution_insight_brief_latest.md"


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return obj if isinstance(obj, dict) else None


def _utc_date_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _pick_thin_row(
    report: dict[str, Any], calendar_date: str | None
) -> tuple[dict[str, Any] | None, str | None]:
    rows = report.get("rows")
    if not isinstance(rows, list):
        return None, None
    if calendar_date:
        for r in rows:
            if isinstance(r, dict) and r.get("calendar_date") == calendar_date:
                return r, calendar_date
    for r in reversed(rows):
        if not isinstance(r, dict):
            continue
        lo = r.get("lens_outputs")
        if not isinstance(lo, dict):
            continue
        ldr = lo.get("logos_dual_regime")
        if ldr:
            return r, str(r.get("calendar_date") or "")
    return None, None


def _fmt_row_note(thin_path: Path, picked_date: str | None, ok: bool) -> str:
    if ok:
        return f"`{thin_path.as_posix()}` row `calendar_date={picked_date}`"
    return f"`{thin_path.as_posix()}` — no populated `logos_dual_regime` row (run thin harness with `--populate-default-samples`)"


def build_markdown(
    *,
    brief_date_utc: str,
    workspace_anchor: str,
    fusion: dict[str, Any] | None,
    thin: dict[str, Any] | None,
    thin_path: Path,
    fusion_path: Path,
    calendar_date: str | None,
) -> str:
    lines: list[str] = []
    lines.append("# Daily execution insight — 1-page brief (generated)")
    lines.append("")
    lines.append("**AUTO:** `scripts/build_daily_execution_insight_brief_v1.py` — Fact-Lock sources only; not LLM prose.")
    lines.append("")
    lines.append("## 0) Meta")
    lines.append("")
    lines.append(f"| `brief_date_utc` | {brief_date_utc} |")
    lines.append(f"| `workspace_anchor` | {workspace_anchor} |")
    lines.append("| `mode` | `OBSERVATION_ONLY` |")
    lines.append("")
    lines.append("## 1) Execution facts (disk)")
    lines.append("")
    lines.append("### 1a) Dual regime (snippet only — no full `interpretation` in brief)")
    lines.append("")
    snippet = ""
    cap_s = "—"
    shock_s = "—"
    veto_s = "—"
    thin_ok = False
    picked_date: str | None = None
    row_note = _fmt_row_note(thin_path, None, False)

    if thin:
        row, picked_date = _pick_thin_row(thin, calendar_date)
        if row:
            lo = row.get("lens_outputs")
            if isinstance(lo, dict):
                ldr = lo.get("logos_dual_regime")
                if isinstance(ldr, dict):
                    thin_ok = True
                    snippet = str(ldr.get("interpretation_snippet") or "").strip()
                    cap = ldr.get("risk_multiplier_cap")
                    cap_s = str(cap) if cap is not None else "—"
                    shock_s = str(ldr.get("market_shock_confirmed"))
                    veto_s = str(ldr.get("veto_triggered"))
                    row_note = _fmt_row_note(thin_path, picked_date or calendar_date, True)

    if not snippet:
        snippet = (
            "*(missing — ensure thin report is written to "
            f"`{thin_path.as_posix()}` with populated `interpretation_snippet`)*"
        )

    lines.append(f"- **Thin row:** {row_note}")
    lines.append("")
    lines.append("**`interpretation_snippet`:**")
    lines.append("")
    lines.append("```")
    lines.append(snippet)
    lines.append("```")
    lines.append("")
    lines.append(
        f"**Snapshot (one line):** `risk_multiplier_cap` = {cap_s} · "
        f"`market_shock_confirmed` = {shock_s} · `veto_triggered` = {veto_s}"
    )
    lines.append("")
    lines.append("### 1b) Independent lens fusion stub (`conflict_summary`)")
    lines.append("")
    lines.append(f"- **Source:** `{fusion_path.as_posix()}`")
    lines.append("")
    narrative = ""
    minority: list[str] = []
    verses: list[str] = []
    if fusion:
        cs = fusion.get("conflict_summary")
        if isinstance(cs, dict):
            narrative = str(cs.get("conflict_narrative_guarded") or "").strip()
            mi = cs.get("minority_lens_ids")
            if isinstance(mi, list):
                minority = [str(x) for x in mi]
            lv = cs.get("logos_evidence_verse_ids")
            if isinstance(lv, list):
                verses = [str(x) for x in lv]

    lines.append(f"- **`minority_lens_ids`:** `{json.dumps(minority, ensure_ascii=False)}`")
    lines.append(f"- **`logos_evidence_verse_ids`:** `{json.dumps(verses, ensure_ascii=False)}`")
    lines.append("")
    lines.append("**`conflict_narrative_guarded`:**")
    lines.append("")
    lines.append("```")
    lines.append(narrative or "*(missing fusion artifact)*")
    lines.append("```")
    lines.append("")
    lines.append("## 2) Hypothesis / insight ([HYPO] — not A-track trigger)")
    lines.append("")
    lines.append("| item | memo |")
    lines.append("|------|------|")
    lines.append("| hypothesis one-liner | *(operator)* |")
    lines.append("| next check script / artifact | *(operator)* |")
    lines.append("")
    lines.append("## 3) Final action (gate vocabulary only)")
    lines.append("")
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append("| `final_action_label` | *(operator)* |")
    lines.append(
        "| `evidence_paths` | "
        f"`{thin_path.as_posix()}`; `{fusion_path.as_posix()}` |"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append(
        f"_thin_ok={thin_ok} calendar_pick={picked_date or 'fallback-or-none'} "
        f"fusion_ok={bool(narrative)}_"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    p.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    p.add_argument("--thin-json", type=Path, default=DEFAULT_THIN)
    p.add_argument("--out", type=Path, default=DEFAULT_OUT)
    p.add_argument(
        "--brief-date-utc",
        default="",
        help="YYYY-MM-DD (UTC). Default: today's UTC date.",
    )
    p.add_argument("--workspace-anchor", default="BTC spot / operator anchor — set via CLI if needed")
    p.add_argument(
        "--calendar-date",
        default="",
        help="Prefer this calendar_date row in thin report (YYYY-MM-DD). Default: match brief-date, then last populated row.",
    )
    p.add_argument(
        "--also-dated-copy",
        action="store_true",
        help="Also write reports/daily_execution_insight_brief_YYYY-MM-DD.md",
    )
    args = p.parse_args()
    root = args.workspace_root.resolve()
    brief_date = args.brief_date_utc.strip() or _utc_date_today()
    cal = args.calendar_date.strip() or brief_date

    fusion_path = args.fusion_json
    thin_path = args.thin_json
    if not fusion_path.is_absolute():
        fusion_path = (root / fusion_path).resolve()
    if not thin_path.is_absolute():
        thin_path = (root / thin_path).resolve()

    fusion = _read_json(fusion_path)
    thin = _read_json(thin_path)

    body = build_markdown(
        brief_date_utc=brief_date,
        workspace_anchor=args.workspace_anchor,
        fusion=fusion,
        thin=thin,
        thin_path=thin_path,
        fusion_path=fusion_path,
        calendar_date=cal,
    )

    out = args.out
    if not out.is_absolute():
        out = (root / out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(body, encoding="utf-8")
    print(f"WROTE: {out}")

    if args.also_dated_copy:
        dated = root / "reports" / f"daily_execution_insight_brief_{brief_date}.md"
        dated.parent.mkdir(parents=True, exist_ok=True)
        dated.write_text(body, encoding="utf-8")
        print(f"WROTE: {dated}")


if __name__ == "__main__":
    main()
