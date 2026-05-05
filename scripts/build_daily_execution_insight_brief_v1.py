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
_ART = WORKSPACE_ROOT / "docs" / "final" / "artifacts"
DEFAULT_MYEONGNI_LENS = _ART / "myeongni_independent_lens_latest.json"
DEFAULT_SASANG_LENS = _ART / "sasang_independent_lens_latest.json"
DEFAULT_MARKET_SASANG_LENS = _ART / "market_sasang_lens_latest.json"
DEFAULT_LOGOS_INDEPENDENT_LENS = _ART / "logos_independent_lens_latest.json"


def _abs_under_root(root: Path, p: Path) -> Path:
    return p.resolve() if p.is_absolute() else (root / p).resolve()


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


def _md_cell(val: Any) -> str:
    s = "" if val is None else str(val)
    return s.replace("|", "\\|").replace("\n", " ").strip()


def _num_opt(x: Any, nd: int = 4) -> str:
    if isinstance(x, bool):
        return str(x)
    try:
        if x is None:
            return "—"
        f = float(x)
        if f != f:
            return "—"
        return f"{f:.{nd}g}"
    except (TypeError, ValueError):
        return _md_cell(x)


def _fmt_row_note(thin_path: Path, picked_date: str | None, ok: bool) -> str:
    if ok:
        return f"`{thin_path.as_posix()}` row `calendar_date={picked_date}`"
    return f"`{thin_path.as_posix()}` — no populated `logos_dual_regime` row (run thin harness with `--populate-default-samples`)"


def _lines_myeongni(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Myeongni (`myeongni_independent_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    mso = doc.get("myeongri_stream_outputs")
    mso = mso if isinstance(mso, dict) else {}
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append(f"| `schema` | {_md_cell(doc.get('schema'))} |")
    lines.append(f"| `direction_score` | {_num_opt(scores.get('direction_score'))} |")
    lines.append(f"| `confidence` | {_num_opt(scores.get('confidence'))} |")
    lines.append(f"| `state_id` | {_md_cell(mso.get('state_id'))} |")
    lines.append(f"| `run_id` | {_md_cell(mso.get('run_id'))} |")
    lines.append("")
    return lines, True


def _lines_sasang(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Sasang (`sasang_independent_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    sso = doc.get("sasang_stream_outputs")
    sso = sso if isinstance(sso, dict) else {}
    mr = sso.get("machine_readables")
    mr = mr if isinstance(mr, dict) else {}
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append(f"| `mapping_target` | {_md_cell(sso.get('mapping_target'))} |")
    lines.append(f"| `regime_hypothesis` | {_md_cell(sso.get('regime_hypothesis'))} |")
    lines.append(f"| `direction_score` | {_num_opt(scores.get('direction_score'))} |")
    lines.append(f"| `confidence` | {_num_opt(scores.get('confidence'))} |")
    lines.append(f"| `heat_proxy` | {_num_opt(mr.get('heat_proxy'))} |")
    lines.append(f"| `cold_proxy` | {_num_opt(mr.get('cold_proxy'))} |")
    lines.append("")
    return lines, True


def _lines_market_sasang(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Market Sasang (`market_sasang_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    hcg = doc.get("human_commander_gate_v1")
    hcg = hcg if isinstance(hcg, dict) else {}
    sv = doc.get("state_vector_sasang_softmax")
    sv = sv if isinstance(sv, dict) else {}
    unc = doc.get("uncertainty")
    unc = unc if isinstance(unc, dict) else {}
    veto = doc.get("veto")
    veto = veto if isinstance(veto, dict) else {}
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append("")
    lines.append(f"- **human_commander banner:** {_md_cell(hcg.get('banner_ko'))}")
    lines.append(
        f"- **`veto.force_hold`:** `{_md_cell(veto.get('force_hold'))}` · "
        f"`reason_codes` = `{json.dumps(veto.get('reason_codes'), ensure_ascii=False)}`"
    )
    lines.append(
        f"- **`composite_uncertainty`:** {_num_opt(unc.get('composite_uncertainty'))} · "
        f"`entropy_norm_4way` = {_num_opt(unc.get('entropy_norm_4way'))}"
    )
    lines.append("")
    lines.append("| softmax key | p |")
    lines.append("|-------------|---|")
    for k in ("taeyang", "soyang", "taeeum", "soeum"):
        lines.append(f"| `{k}` | {_num_opt(sv.get(k))} |")
    lines.append("")
    return lines, True


def _lines_logos_independent(doc: dict[str, Any] | None, path: Path) -> tuple[list[str], bool]:
    lines: list[str] = []
    lines.append("#### Logos independent lens (`logos_independent_lens_latest`)")
    lines.append("")
    if not doc:
        lines.append(f"*(missing — `{path.as_posix()}`)*")
        lines.append("")
        return lines, False
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    ev = doc.get("evidence_refs")
    n_ev = len(ev) if isinstance(ev, list) else 0
    lines.append("| field | value |")
    lines.append("|-------|-------|")
    lines.append(f"| `ts_utc` | {_md_cell(doc.get('ts_utc'))} |")
    lines.append(f"| `direction_score` | {_num_opt(scores.get('direction_score'))} |")
    lines.append(f"| `confidence` | {_num_opt(scores.get('confidence'))} |")
    lines.append(f"| `evidence_refs_count` | {n_ev} |")
    lines.append("")
    narr = str(doc.get("narrative_snippet_guarded") or "").strip()
    lines.append("**`narrative_snippet_guarded` (hash-tagged only):**")
    lines.append("")
    lines.append("```")
    lines.append(narr or "*(empty)*")
    lines.append("```")
    lines.append("")
    return lines, True


def build_markdown(
    *,
    brief_date_utc: str,
    workspace_anchor: str,
    fusion: dict[str, Any] | None,
    thin: dict[str, Any] | None,
    thin_path: Path,
    fusion_path: Path,
    calendar_date: str | None,
    myeongni: dict[str, Any] | None = None,
    myeongni_path: Path | None = None,
    sasang: dict[str, Any] | None = None,
    sasang_path: Path | None = None,
    market_sasang: dict[str, Any] | None = None,
    market_sasang_path: Path | None = None,
    logos_independent: dict[str, Any] | None = None,
    logos_independent_path: Path | None = None,
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
    lines.append("### 1c) Independent lens snapshots (latest JSON — numeric / structured facts only)")
    lines.append("")
    mp = myeongni_path or DEFAULT_MYEONGNI_LENS
    sp = sasang_path or DEFAULT_SASANG_LENS
    msp = market_sasang_path or DEFAULT_MARKET_SASANG_LENS
    lp = logos_independent_path or DEFAULT_LOGOS_INDEPENDENT_LENS
    lm, ok_m = _lines_myeongni(myeongni, mp)
    ls, ok_s = _lines_sasang(sasang, sp)
    lms, ok_ms = _lines_market_sasang(market_sasang, msp)
    ll, ok_l = _lines_logos_independent(logos_independent, lp)
    lines.extend(lm)
    lines.extend(ls)
    lines.extend(lms)
    lines.extend(ll)
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
    ev_paths = (
        f"`{thin_path.as_posix()}`; `{fusion_path.as_posix()}`; "
        f"`{mp.as_posix()}`; `{sp.as_posix()}`; `{msp.as_posix()}`; `{lp.as_posix()}`"
    )
    lines.append(f"| `evidence_paths` | {ev_paths} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    ind_flags = {
        "myeongni": ok_m,
        "sasang": ok_s,
        "market_sasang": ok_ms,
        "logos_independent": ok_l,
    }
    lines.append(
        "_Generator flags:_ "
        f"`thin_ok={thin_ok}` `calendar_pick={picked_date or 'fallback-or-none'}` "
        f"`fusion_ok={bool(narrative)}` "
        f"`independent_lens_ok={json.dumps(ind_flags, ensure_ascii=False)}`"
    )
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace-root", type=Path, default=WORKSPACE_ROOT)
    p.add_argument("--fusion-json", type=Path, default=DEFAULT_FUSION)
    p.add_argument("--thin-json", type=Path, default=DEFAULT_THIN)
    p.add_argument("--myeongni-json", type=Path, default=DEFAULT_MYEONGNI_LENS)
    p.add_argument("--sasang-json", type=Path, default=DEFAULT_SASANG_LENS)
    p.add_argument("--market-sasang-json", type=Path, default=DEFAULT_MARKET_SASANG_LENS)
    p.add_argument("--logos-independent-json", type=Path, default=DEFAULT_LOGOS_INDEPENDENT_LENS)
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

    fusion_path = _abs_under_root(root, args.fusion_json)
    thin_path = _abs_under_root(root, args.thin_json)
    myeongni_path = _abs_under_root(root, args.myeongni_json)
    sasang_path = _abs_under_root(root, args.sasang_json)
    market_sasang_path = _abs_under_root(root, args.market_sasang_json)
    logos_independent_path = _abs_under_root(root, args.logos_independent_json)

    fusion = _read_json(fusion_path)
    thin = _read_json(thin_path)
    myeongni = _read_json(myeongni_path)
    sasang = _read_json(sasang_path)
    market_sasang = _read_json(market_sasang_path)
    logos_independent = _read_json(logos_independent_path)

    body = build_markdown(
        brief_date_utc=brief_date,
        workspace_anchor=args.workspace_anchor,
        fusion=fusion,
        thin=thin,
        thin_path=thin_path,
        fusion_path=fusion_path,
        calendar_date=cal,
        myeongni=myeongni,
        myeongni_path=myeongni_path,
        sasang=sasang,
        sasang_path=sasang_path,
        market_sasang=market_sasang,
        market_sasang_path=market_sasang_path,
        logos_independent=logos_independent,
        logos_independent_path=logos_independent_path,
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
