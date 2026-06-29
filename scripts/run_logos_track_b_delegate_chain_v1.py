#!/usr/bin/env python3
"""Logos Track B delegate chain — themed push + vector + Ollama distill (all themes)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_DEFAULT = ROOT / "reports/logos_track_b_delegate_chain_v1_latest.json"
THEMES = ("dan_aramaic", "john_1_logos")
SMOKE_REPORT = ROOT / "reports/ollama_local_smoke_v1_latest.json"
ART = ROOT / "docs/final/artifacts"
REPORTS = ROOT / "reports"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _run(name: str, cmd: list[str]) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-500:],
        "stderr_tail": (proc.stderr or "")[-200:],
        "ok": proc.returncode == 0,
    }


def _paths(theme_id: str) -> dict[str, Path]:
    return {
        "distill": ART / f"logos_deep_research_distill_{theme_id}_latest.json",
        "distill_locked": ART / f"logos_deep_research_distill_{theme_id}_citation_lock_latest.json",
        "commander_json": ART / f"logos_track_b_commander_deep_report_{theme_id}_latest.json",
        "commander_md": REPORTS / f"logos_track_b_commander_deep_report_{theme_id}_latest.md",
        "vector_query": ART / f"logos_themed_vector_query_{theme_id}_latest.json",
    }


def _smoke_fresh(max_age_sec: int = 3600) -> bool:
    if not SMOKE_REPORT.is_file():
        return False
    try:
        doc = json.loads(SMOKE_REPORT.read_text(encoding="utf-8-sig"))
        ts = doc.get("generated_at_utc") or doc.get("ts_utc") or ""
        if not ts:
            return doc.get("ok") is True
        from datetime import datetime

        then = datetime.strptime(ts[:19], "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - then).total_seconds()
        return doc.get("ok") is True and age <= max_age_sec
    except (json.JSONDecodeError, ValueError, OSError):
        return False


def _ollama_refresh_theme(theme_id: str, steps: list[dict[str, Any]], repro: str) -> None:
    p = _paths(theme_id)
    if not p["distill"].is_file():
        return
    steps.append(
        _run(
            f"ollama_citation_lock_{theme_id}",
            [
                PY,
                "scripts/run_logos_llm_distill_citation_lock_v1.py",
                "--allow-llm-distill",
                "--input",
                str(p["distill"]),
                "--output",
                str(p["distill_locked"]),
            ],
        )
    )
    steps.append(
        _run(
            f"commander_refresh_{theme_id}",
            [
                PY,
                "scripts/run_logos_track_b_commander_deep_report_v1.py",
                "--distill-json",
                str(p["distill_locked"]),
                "--output",
                str(p["commander_json"]),
            ],
        )
    )
    steps.append(
        _run(
            f"commander_md_{theme_id}",
            [
                PY,
                "scripts/build_logos_track_b_commander_report_md_v1.py",
                "--input",
                str(p["commander_json"]),
                "--distill",
                str(p["distill_locked"]),
                "--output",
                str(p["commander_md"]),
                "--reproduce-cmd",
                repro,
            ],
        )
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-ollama-smoke", action="store_true")
    ap.add_argument(
        "--reuse-ollama-smoke",
        action="store_true",
        help="Skip smoke when reports/ollama_local_smoke_v1_latest.json is fresh (<1h).",
    )
    ap.add_argument(
        "--try-ollama-distill",
        action="store_true",
        help="Run citation-lock Ollama distill for all themes when smoke ok.",
    )
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    repro = "py scripts/run_logos_track_b_delegate_chain_v1.py --try-ollama-distill --reuse-ollama-smoke"
    steps: list[dict[str, Any]] = []
    steps.append(_run("themed_deep_push", [PY, "scripts/run_logos_track_b_themed_deep_push_v1.py"]))

    ollama_ok = False
    if args.skip_ollama_smoke:
        ollama_ok = _smoke_fresh()
    elif args.reuse_ollama_smoke and _smoke_fresh():
        ollama_ok = True
        steps.append(
            {
                "name": "ollama_smoke_reused",
                "ok": True,
                "elapsed_sec": 0,
                "stdout_tail": "fresh smoke report reused",
                "stderr_tail": "",
                "exit_code": 0,
            }
        )
    else:
        smoke = _run("ollama_smoke", [PY, "scripts/ollama_local_smoke_v1.py"])
        steps.append(smoke)
        ollama_ok = smoke.get("ok", False)

    llm_themes: list[str] = []
    if args.try_ollama_distill and ollama_ok:
        os.environ["MKM_LOGOS_LLM_DISTILL_ENABLE"] = "1"
        for tid in THEMES:
            llm_themes.append(tid)
            _ollama_refresh_theme(tid, steps, repro)

    theme_summaries: list[dict[str, Any]] = []
    for tid in THEMES:
        p = _paths(tid)
        locked = {}
        if p["distill_locked"].is_file():
            try:
                locked = json.loads(p["distill_locked"].read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                locked = {}
        narr = locked.get("distill_narrative_stub_ko") or {}
        vec_hits = 0
        if p["vector_query"].is_file():
            try:
                vq = json.loads(p["vector_query"].read_text(encoding="utf-8-sig"))
                vec_hits = len(vq.get("top_k") or [])
            except json.JSONDecodeError:
                vec_hits = 0
        theme_summaries.append(
            {
                "theme_id": tid,
                "evidence_refs": len(locked.get("evidence_refs") or []),
                "citation_locked": (locked.get("citation_lock") or {}).get("locked_count"),
                "themed_vector_hits": vec_hits,
                "llm_invoked": narr.get("llm_invoked"),
                "citation_valid": narr.get("citation_valid"),
                "commander_md": str(p["commander_md"].relative_to(ROOT)).replace("\\", "/"),
            }
        )

    themed_ok = steps[0].get("ok", False) if steps else False
    summary = {
        "schema": "logos_track_b_delegate_chain_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "non_gating_ack": True,
        "ollama_smoke_ok": ollama_ok,
        "llm_distill_themes": llm_themes,
        "mkm_logos_llm_distill_enable": _truthy("MKM_LOGOS_LLM_DISTILL_ENABLE"),
        "themes": theme_summaries,
        "steps": steps,
        "themed_ok": themed_ok,
        "all_ok": themed_ok,
        "reproduce": repro,
    }

    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": summary["all_ok"], "out": str(out_path.relative_to(ROOT))}, ensure_ascii=False))
    return 0 if summary["all_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
