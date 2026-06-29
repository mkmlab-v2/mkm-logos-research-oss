#!/usr/bin/env python3
"""Auto-continue Logos Track B + MS paste — one command for operator loop."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
REPORTS = ROOT / "reports"
OUT_DEFAULT = REPORTS / "logos_track_b_auto_continue_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(name: str, cmd: list[str], *, timeout: int = 3600) -> dict[str, Any]:
    t0 = time.perf_counter()
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    return {
        "name": name,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-300:],
        "ok": proc.returncode == 0,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    ap.add_argument("--skip-ollama", action="store_true")
    ap.add_argument("--skip-phase-l", action="store_true")
    ap.add_argument("--reuse-ollama-smoke", action="store_true", default=True)
    ap.add_argument("--no-reuse-ollama-smoke", action="store_false", dest="reuse_ollama_smoke")
    ap.add_argument("--insight-synthesis", action="store_true", default=True, help="Run Phase N (default on)")
    ap.add_argument("--skip-insight-synthesis", action="store_true", help="Skip Phase N")
    ap.add_argument("--phase-o", action="store_true", default=True, help="Run Phase O (default on)")
    ap.add_argument("--skip-phase-o", action="store_true", help="Skip Phase O")
    ap.add_argument("--clipboard", action="store_true", help="Copy MS paste bundle to clipboard after refresh")
    ap.add_argument("--include-sasang-41k", action="store_true", default=True)
    ap.add_argument("--skip-sasang-41k", action="store_true", help="Skip B-track Sasang-41k auto-continue")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []

    if not args.skip_phase_l:
        l_cmd = [PY, "scripts/run_logos_track_b_phase_l_v1.py"]
        if args.skip_ollama:
            l_cmd.append("--skip-ollama")
        elif args.reuse_ollama_smoke:
            l_cmd.append("--reuse-ollama-smoke")
        steps.append(_run("phase_l", l_cmd, timeout=3600))
    else:
        steps.append({"name": "phase_l_skipped", "ok": True})

    steps.append(_run("phase_m", [PY, "scripts/run_logos_track_b_phase_m_v1.py"], timeout=1200))

    if args.insight_synthesis and not args.skip_insight_synthesis:
        n_cmd = [PY, "scripts/run_logos_track_b_phase_n_v1.py", "--max-insight-units", "12"]
        if args.skip_ollama:
            n_cmd.append("--skip-ollama")
        steps.append(_run("phase_n_insight", n_cmd, timeout=7200))

    if args.phase_o and not args.skip_phase_o:
        steps.append(_run("phase_o_hot_reload", [PY, "scripts/run_logos_track_b_hot_reload_v1.py"], timeout=900))
        steps.append(
            _run(
                "logos_research_commercial_pack",
                [PY, "scripts/run_logos_research_commercial_pack_v1.py", "--skip-phase-o"],
                timeout=300,
            )
        )
        steps.append(_run("tracka_logic_weights_shadow", [PY, "scripts/extract_logic_weights_for_track_a_v1.py"], timeout=300))
        steps.append(_run("tracka_shadow_default_preset", [PY, "scripts/build_tracka_shadow_default_preset_v1.py", "--skip-perf"], timeout=300))
        steps.append(
            _run(
                "tracka_compression_perf_shadow",
                [
                    PY,
                    "scripts/run_compression_perf_test_v1.py",
                    "--logic-aware-shadow",
                    "--weights",
                    "reports/tracka_logic_weights_shadow_preset_v1_latest.json",
                    "--out",
                    "reports/compression_perf_test_preset_v1_latest.json",
                ],
                timeout=1200,
            )
        )
        steps.append(
            _run(
                "tracka_optimization_impact_shadow",
                [
                    PY,
                    "scripts/report_optimization_impact_v1.py",
                    "--perf",
                    "reports/compression_perf_test_preset_v1_latest.json",
                    "--out",
                    "reports/optimization_impact_preset_v1_latest.json",
                    "--out-md",
                    "reports/optimization_impact_preset_v1_latest.md",
                ],
                timeout=300,
            )
        )

    if args.include_sasang_41k and not args.skip_sasang_41k:
        steps.append(
            _run(
                "sasang_41k_auto_continue",
                [PY, "scripts/run_btrack_sasang_41k_auto_continue_v1.py", "--skip-logos-pack"],
                timeout=600,
            )
        )
        steps.append(
            _run(
                "lexicon_4d_research_audit",
                [PY, "scripts/run_logos_lexicon_4d_research_audit_v1.py", "--skip-phase-pa"],
                timeout=3600,
            )
        )

    paste_cmd = [PY, "scripts/refresh_ms_proposal_paste_artifacts_v1.py"]
    if args.clipboard:
        paste_cmd.append("--clipboard")
    steps.append(_run("ms_paste_refresh", paste_cmd, timeout=300))

    paste_doc: dict[str, Any] = {}
    paste_path = REPORTS / "ms_proposal_paste_ready_v1_latest.json"
    if paste_path.is_file():
        try:
            paste_doc = json.loads(paste_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass

    closure: dict[str, Any] = {}
    closure_path = REPORTS / "logos_track_b_integration_closure_v1_latest.json"
    if closure_path.is_file():
        try:
            closure = json.loads(closure_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass

    overall_ok = all(s.get("ok") for s in steps) and closure.get("ok") is True
    doc = {
        "schema": "logos_track_b_auto_continue_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "integration_closure_ok": closure.get("ok"),
        "ms_paste_ready": paste_doc.get("paste_ready"),
        "clipboard_ok": (paste_doc.get("clipboard") or {}).get("ok"),
        "automated": [
            "Ollama themed deep push (when up)",
            "graph_paths sync + commander digest",
            "MS evidence pack + one_pager regeneration",
            "Logos Track B MS sub-bundle",
            "MACULA TSV auto-discover (when path exists)",
            "Phase O Psi logic transplant + simplicial ledger (default on)",
            "B-track Sasang-41k shadow + Psi role bridge (default on)",
            "logos.jema-ai.com product metrics + commercial manifest",
            "lexicon 4D projection audit + path gate shadow (NON_GATING)",
            "Track A compression shadow optimization report (NON_GATING)",
            "Track A shadow default preset from Pareto sweep (NON_GATING)",
        ],
        "human_gates_remain": paste_doc.get("human_gates_remain") or [],
        "steps": steps,
        "ok": overall_ok,
        "reproduce": "py scripts/run_logos_track_b_auto_continue_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": overall_ok, "ms_paste_ready": paste_doc.get("paste_ready"), "out": str(args.out)}, ensure_ascii=False))
    return 0 if overall_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
