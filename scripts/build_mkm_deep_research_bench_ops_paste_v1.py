#!/usr/bin/env python3
"""Build commander ops paste from DR bench mini latest JSON (internal briefing, B-track)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BENCH = ROOT / "reports" / "mkm_deep_research_bench_mini_v1_latest.json"
OUT_MD = ROOT / "reports" / "mkm_deep_research_bench_ops_paste_v1_latest.md"
OUT_JSON = ROOT / "reports" / "mkm_deep_research_bench_ops_paste_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pct(x: float | None) -> str:
    if x is None:
        return "n/a"
    return f"{round(float(x) * 100, 2):.2f}%"


def _load_bench(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"missing bench json: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _task_table_rows(tasks: list[dict[str, Any]]) -> str:
    lines = [
        "| task | citation | support | rows | baseline/challenge | plane | entry-level |",
        "|------|----------|---------|------|--------------------|-------|-------------|",
    ]
    for t in tasks:
        diff = t.get("difficulty_counts") or {}
        bc = f"{diff.get('baseline', 0)}/{diff.get('challenge', 0)}"
        plane_ok = "yes" if t.get("research_plane_match") else "no"
        if t.get("research_plane_match") is None:
            plane_ok = "n/a"
        entry = "yes" if not t.get("difficulty_pass_metrics_fallback_used") else "fallback"
        lines.append(
            "| {id} | {cit} | {sup} | {rows} | {bc} | {plane} ({plane_ok}) | {entry} |".format(
                id=t.get("id"),
                cit=_pct(t.get("citation_pass_rate")),
                sup=_pct(t.get("support_pass_rate")),
                rows=t.get("fixture_rows"),
                bc=bc,
                plane=t.get("research_plane_expected") or "n/a",
                plane_ok=plane_ok,
                entry=entry,
            )
        )
    return "\n".join(lines) + "\n"


def _rel_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def build_paste(
    bench: dict[str, Any],
    *,
    copy_approved: bool = False,
    commander_signoff_at: str | None = None,
    commander_signoff_note: str | None = None,
) -> tuple[str, dict[str, Any]]:
    metrics = bench.get("metrics") or {}
    tasks = bench.get("tasks") or []
    diff_rows = metrics.get("difficulty_rows_total") or {}
    diff_rate = metrics.get("difficulty_pass_rate") or {}
    entry_map = metrics.get("difficulty_entry_mapping") or {}
    digest = metrics.get("digestion_pass_metrics") or {}
    mode = bench.get("mode") or "unknown"
    gate_ok = bool(bench.get("ok") and metrics.get("gate_ok"))

    ko_lines = "\n".join(
        [
            "딥리서치 DR bench mini(7-task) — citation/support 이중 게이트 + TCM + digestion extensions 통과 여부를 주간 점검합니다.",
            f"모드: {mode} · task {metrics.get('tasks_ok', 0)}/{metrics.get('task_count', 0)} OK.",
            f"citation mean {_pct(metrics.get('citation_pass_rate_mean'))} · support mean {_pct(metrics.get('support_pass_rate_mean'))}.",
            f"난이도 baseline {diff_rows.get('baseline', 0)}행 / challenge {diff_rows.get('challenge', 0)}행 — entry-level fallback {entry_map.get('fallback_used_task_count', 0)}건.",
        ]
    )
    if digest:
        ko_lines += (
            f"\n소화(digestion): facts {digest.get('fact_count', 0)} · wiring_rate_mean "
            f"{_pct(digest.get('wiring_rate_mean'))} · gate_pass_rate_mean "
            f"{_pct(digest.get('gate_pass_rate_mean'))} · digestion_gate_ok {metrics.get('digestion_gate_ok')}."
        )
    ko_lines += "\nTrack B · research_only · send_gate HOLD — Track A 승격·실매매 트리거 아님."

    md = f"""# DR bench mini — Commander ops paste v1

**generated_at_utc:** {_utc_now()}  
**paste_build_ok:** {str(gate_ok).lower()}  
**bench_gate_ok:** {str(gate_ok).lower()}  
**paste_copy_approved:** {str(copy_approved).lower()} *(commander signoff only)*  
**commander_signoff_at:** {commander_signoff_at or "null"}  
**bench_mode:** `{mode}`  
**send_gate:** `HOLD` *(B-track research_only — no external send)*  
**reproduce:** `py scripts/build_mkm_deep_research_bench_ops_paste_v1.py`

Internal ops briefing from `reports/mkm_deep_research_bench_mini_v1_latest.json` — not public-facing copy.

---

## Commander one-screen (KO)

{ko_lines}

---

## Headline metrics (dual report)

| metric | value |
|--------|-------|
| tasks_ok / task_count | {metrics.get('tasks_ok', 0)} / {metrics.get('task_count', 0)} |
| citation_pass_rate_mean | {_pct(metrics.get('citation_pass_rate_mean'))} |
| support_pass_rate_mean | {_pct(metrics.get('support_pass_rate_mean'))} |
| baseline rows | {diff_rows.get('baseline', 0)} |
| challenge rows | {diff_rows.get('challenge', 0)} |
| baseline citation (row-level) | {_pct((diff_rate.get('baseline') or {}).get('citation'))} |
| baseline support (row-level) | {_pct((diff_rate.get('baseline') or {}).get('support'))} |
| challenge citation (row-level) | {_pct((diff_rate.get('challenge') or {}).get('citation'))} |
| challenge support (row-level) | {_pct((diff_rate.get('challenge') or {}).get('support'))} |
| entry-level fallback tasks | {entry_map.get('fallback_used_task_count', 0)} |
| difficulty_gate_ok | {metrics.get('difficulty_gate_ok', False)} |
| digestion_gate_ok | {metrics.get('digestion_gate_ok', 'n/a')} |
| digestion gate_pass_rate_mean | {_pct(digest.get('gate_pass_rate_mean')) if digest else 'n/a'} |
| digestion wiring_rate_mean | {_pct(digest.get('wiring_rate_mean')) if digest else 'n/a'} |
| require_entry_level (last run) | {entry_map.get('require_entry_level', False)} |

---

## Per-task table

{_task_table_rows(tasks)}

---

## Reproduce

```powershell
py -m pytest tests/test_mkm_deep_research_bench_mini_v1.py -q
py scripts/run_mkm_deep_research_bench_mini_v1.py --offline --include-router --require-entry-level
py scripts/run_mkm_deep_research_bench_mini_v1.py --include-router --require-entry-level
py scripts/build_mkm_deep_research_bench_ops_paste_v1.py
powershell -File scripts\\Invoke-MkmDeepResearchBenchWeekly_v1.ps1
```

Source bench JSON: `{bench.get('tasks_spec', 'tests/fixtures/mkm_deep_research_bench_tasks_v1.json')}`
"""

    doc = {
        "schema": "mkm_deep_research_bench_ops_paste_v1",
        "generated_at_utc": _utc_now(),
        "paste_build_ok": gate_ok,
        "bench_gate_ok": gate_ok,
        "paste_copy_approved": copy_approved,
        "paste_copy_approved_by": "commander" if copy_approved else None,
        "commander_signoff_at": commander_signoff_at,
        "commander_signoff_note": commander_signoff_note,
        "commander_review_only": not copy_approved,
        "bench_mode": mode,
        "send_gate": "HOLD",
        "research_only": True,
        "track_b_only": True,
        "markdown_path": "reports/mkm_deep_research_bench_ops_paste_v1_latest.md",
        "bench_json_path": "reports/mkm_deep_research_bench_mini_v1_latest.json",
        "reproduce": "py scripts/build_mkm_deep_research_bench_ops_paste_v1.py",
        "headline": {
            "task_count": metrics.get("task_count"),
            "tasks_ok": metrics.get("tasks_ok"),
            "citation_pass_rate_mean": metrics.get("citation_pass_rate_mean"),
            "support_pass_rate_mean": metrics.get("support_pass_rate_mean"),
            "difficulty_rows_total": diff_rows,
            "difficulty_pass_rate": diff_rate,
            "entry_mapping": entry_map,
            "digestion_pass_metrics": digest or None,
            "digestion_gate_ok": metrics.get("digestion_gate_ok"),
        },
    }
    return md, doc


def main() -> int:
    parser = argparse.ArgumentParser(description="Build DR bench ops paste from latest bench JSON")
    parser.add_argument("--input", type=Path, default=DEFAULT_BENCH)
    parser.add_argument("--out-md", type=Path, default=OUT_MD)
    parser.add_argument("--out-json", type=Path, default=OUT_JSON)
    parser.add_argument(
        "--commander-signoff",
        nargs="?",
        const="commander_signoff",
        default=None,
        help="Record commander signoff (optional note). Preserved across rebuilds unless omitted.",
    )
    args = parser.parse_args()

    prior: dict[str, Any] = {}
    if args.out_json.is_file():
        try:
            prior = json.loads(args.out_json.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prior = {}

    signoff_at: str | None = prior.get("commander_signoff_at")
    signoff_note: str | None = prior.get("commander_signoff_note")
    if args.commander_signoff is not None:
        signoff_at = _utc_now()
        signoff_note = args.commander_signoff.strip() or "commander_signoff"
    copy_approved = bool(signoff_at)

    try:
        bench = _load_bench(args.input.resolve())
    except FileNotFoundError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    md, doc = build_paste(
        bench,
        copy_approved=copy_approved,
        commander_signoff_at=signoff_at,
        commander_signoff_note=signoff_note,
    )
    args.out_md.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_md.write_text(md, encoding="utf-8")
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "ok": doc["paste_build_ok"],
        "wrote_md": _rel_path(args.out_md),
        "wrote_json": _rel_path(args.out_json),
        "bench_gate_ok": doc["bench_gate_ok"],
        "paste_copy_approved": doc["paste_copy_approved"],
        "send_gate": "HOLD",
    }
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if doc["paste_build_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
