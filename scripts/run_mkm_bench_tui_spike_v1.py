#!/usr/bin/env python3
"""MKM bench TUI spike — Hero orchestration bench replay (no Ollama required).

Wraps `run_mkm_ltm_orchestration_bench_bundle_v1.py` and renders measured token diet
from `reports/mkm_ltm_orchestration_bench_v1_latest.json`. Optional secondary panel
reads compression open-bench dual report when present (not Hero headline).

  py scripts/run_mkm_bench_tui_spike_v1.py
  py scripts/run_mkm_bench_tui_spike_v1.py --replay-only
  py scripts/run_mkm_bench_tui_spike_v1.py --plain
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
BUNDLE_SCRIPT = ROOT / "scripts/run_mkm_ltm_orchestration_bench_bundle_v1.py"
ORCH_PATH = ROOT / "reports/mkm_ltm_orchestration_bench_v1_latest.json"
BUNDLE_PATH = ROOT / "reports/mkm_ltm_orchestration_bench_bundle_v1_latest.json"
OPEN_BENCH_PATH = ROOT / "reports/compression_open_bench_dual_report_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/mkm_bench_tui_spike_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _pct(ratio: float | None) -> str:
    if ratio is None:
        return "n/a"
    return f"{ratio * 100:.1f}%"


def _run_bundle(*, skip_prior_art_seed: bool = False) -> tuple[int, dict[str, Any]]:
    cmd = [PY, str(BUNDLE_SCRIPT)]
    if skip_prior_art_seed:
        cmd.append("--skip-prior-art-seed")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, timeout=600)
    tail = ((proc.stdout or "") + (proc.stderr or ""))[-1500:]
    bundle_doc: dict[str, Any] = {}
    if BUNDLE_PATH.is_file():
        try:
            bundle_doc = json.loads(BUNDLE_PATH.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            bundle_doc = {}
    return proc.returncode, {"exit_code": proc.returncode, "tail": tail, "bundle_ok": bundle_doc.get("ok")}


def _hero_metrics(orch: dict[str, Any]) -> dict[str, Any]:
    naive = orch.get("naive_baseline") or {}
    shallow_agg = (orch.get("shallow_lane_inject") or {}).get("aggregate") or {}
    orch_path = orch.get("orchestrated_query_path") or {}
    return {
        "naive_baseline_tokens": naive.get("tokens"),
        "shallow_mean_savings_ratio": shallow_agg.get("mean_savings_ratio_vs_naive_baseline"),
        "shallow_mean_savings_pct": _pct(shallow_agg.get("mean_savings_ratio_vs_naive_baseline")),
        "orchestrated_total_tokens": (orch_path.get("aggregate") or {}).get("total_tokens"),
        "orchestrated_savings_ratio": orch_path.get("savings_ratio_vs_naive_baseline"),
        "orchestrated_savings_pct": _pct(orch_path.get("savings_ratio_vs_naive_baseline")),
        "artifact_path": _rel(ORCH_PATH),
        "disclaimer": (
            "Measured vs naive MISSION_LOG+CENTRAL paste baseline — not Cursor cloud bill guarantee."
        ),
    }


def _secondary_open_bench() -> dict[str, Any] | None:
    if not OPEN_BENCH_PATH.is_file():
        return None
    try:
        doc = json.loads(OPEN_BENCH_PATH.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return None
    corpora = doc.get("corpora_and_skus") or []
    first = corpora[0] if corpora else {}
    raw = first.get("raw") or {}
    return {
        "lane": "compression_open_bench_secondary",
        "label": first.get("label"),
        "raw_saving_pct_display": raw.get("saving_pct_display"),
        "mean_jaccard_proxy": raw.get("mean_jaccard_proxy"),
        "artifact_path": _rel(OPEN_BENCH_PATH),
        "note": "Secondary open-bench lane — not Hero headline; not Cursor traffic.",
    }


def _render_plain(hero: dict[str, Any], secondary: dict[str, Any] | None, *, bundle_ok: bool) -> None:
    print("")
    print("MKM bench TUI (plain) — Hero orchestration metrics")
    print("=" * 56)
    print(f"  naive baseline tokens     : {hero.get('naive_baseline_tokens')}")
    print(f"  shallow lane inject save  : {hero.get('shallow_mean_savings_pct')} vs naive")
    print(f"  orchestrated path tokens  : {hero.get('orchestrated_total_tokens')}")
    print(f"  orchestrated path save    : {hero.get('orchestrated_savings_pct')} vs naive")
    print(f"  artifact                  : {hero.get('artifact_path')}")
    print(f"  bundle ok                 : {bundle_ok}")
    print(f"  disclaimer                : {hero.get('disclaimer')}")
    if secondary:
        print("-" * 56)
        print("  [Secondary · open bench — not Hero]")
        print(f"  label                     : {secondary.get('label')}")
        print(f"  raw saving pct (display)  : {secondary.get('raw_saving_pct_display')}")
        print(f"  artifact                  : {secondary.get('artifact_path')}")
    print("=" * 56)
    print("  exit 0 — reproduce: py scripts/run_mkm_bench_tui_spike_v1.py")
    print("")


def _render_rich(hero: dict[str, Any], secondary: dict[str, Any] | None, *, bundle_ok: bool) -> None:
    try:
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
    except ImportError:
        _render_plain(hero, secondary, bundle_ok=bundle_ok)
        return

    console = Console()
    table = Table(title="Hero · LTM orchestration bench (no Ollama)", show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="dim")
    table.add_column("Value", justify="right")
    table.add_row("Naive baseline tokens", str(hero.get("naive_baseline_tokens")))
    table.add_row("Shallow inject savings", hero.get("shallow_mean_savings_pct") or "n/a")
    table.add_row("Orchestrated path tokens", str(hero.get("orchestrated_total_tokens")))
    table.add_row("Orchestrated path savings", hero.get("orchestrated_savings_pct") or "n/a")
    table.add_row("Bundle ok", "yes" if bundle_ok else "no")
    console.print()
    console.print(Panel(table, subtitle=hero.get("disclaimer"), border_style="green"))
    console.print(f"[dim]artifact:[/dim] {hero.get('artifact_path')}")
    if secondary:
        sec = Table(title="Secondary · compression open bench (not Hero)", show_header=True)
        sec.add_column("Field")
        sec.add_column("Value", justify="right")
        sec.add_row("label", str(secondary.get("label")))
        sec.add_row("raw saving % (display)", str(secondary.get("raw_saving_pct_display")))
        sec.add_row("artifact", str(secondary.get("artifact_path")))
        console.print(Panel(sec, border_style="yellow"))
    console.print("[bold green]exit 0[/bold green] · [dim]py scripts/run_mkm_bench_tui_spike_v1.py[/dim]")
    console.print()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--replay-only", action="store_true", help="Skip bundle run; read latest artifacts")
    ap.add_argument("--plain", action="store_true", help="Force plain stdout (no rich)")
    ap.add_argument("--skip-prior-art-seed", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--stdout-only", action="store_true")
    args = ap.parse_args()

    bundle_step: dict[str, Any] = {"skipped": True, "exit_code": 0}
    if not args.replay_only:
        code, bundle_step = _run_bundle(skip_prior_art_seed=args.skip_prior_art_seed)
        if code != 0:
            print(f"error: bench bundle exit {code}", file=sys.stderr)
            print(bundle_step.get("tail", ""), file=sys.stderr)
            return code

    if not ORCH_PATH.is_file():
        print(f"error: missing orchestration bench: {ORCH_PATH}", file=sys.stderr)
        return 2

    orch = json.loads(ORCH_PATH.read_text(encoding="utf-8-sig"))
    hero = _hero_metrics(orch)
    secondary = _secondary_open_bench()
    bundle_ok = bool(bundle_step.get("bundle_ok", True) or args.replay_only)

    if args.plain:
        _render_plain(hero, secondary, bundle_ok=bundle_ok)
    else:
        _render_rich(hero, secondary, bundle_ok=bundle_ok)

    doc: dict[str, Any] = {
        "schema": "mkm_bench_tui_spike_v1",
        "generated_at_utc": _utc_now(),
        "track": "B",
        "research_only": True,
        "hypothesis_tier": "B",
        "ok": True,
        "ollama_required": False,
        "hero_metrics": hero,
        "secondary_open_bench": secondary,
        "bundle_step": bundle_step,
        "reproduce": "py scripts/run_mkm_bench_tui_spike_v1.py",
        "replay_only": "py scripts/run_mkm_bench_tui_spike_v1.py --replay-only",
        "boundary_ack": (
            "Hero numbers from orchestration bench only. "
            "Cursor proxy savings not measured. open_bench is secondary lane."
        ),
    }

    if not args.stdout_only:
        out = args.out_json.resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.plain:
            print(f"WROTE: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
