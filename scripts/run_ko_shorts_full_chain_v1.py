#!/usr/bin/env python3
"""Full ko shorts STT chain: fetch → spike → gate → burn-in → Cursor QA [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.ko_shorts_alignment_routing_lib_v1 import MODE_AUTO  # noqa: E402

DEFAULT_OUT = ROOT / "reports/ko_shorts_full_chain_v1_latest.json"

FETCH = ROOT / "scripts/fetch_ko_shorts_web_speech_wav_v1.py"
TIMING_COMPARE = ROOT / "scripts/run_ko_shorts_timing_compare_v1.py"
GATE_BENCH = ROOT / "scripts/run_ko_shorts_subtitle_gate_bench_v1.py"
BURNIN_BATCH = ROOT / "scripts/run_ko_shorts_ass_burnin_batch_v1.py"
CURSOR_QA = ROOT / "scripts/run_ko_shorts_cursor_ide_qa_v1.py"
QA_CHECKLIST = ROOT / "scripts/build_ko_shorts_manual_tool_qa_checklist_v1.py"
ALIGN_SPIKE = ROOT / "scripts/run_ko_shorts_alignment_backend_spike_v1.py"
SEG_DECISION = ROOT / "scripts/build_ko_shorts_segment_backend_decision_v1.py"
ALIGN_VENV_PY = ROOT / ".venv-ko-shorts-align" / "Scripts" / "python.exe"
ALIGN_SPIKE_OUT = "reports/ko_shorts_alignment_backend_spike_v1_latest.json"
TARGET_WAV_BATCH = ROOT / "scripts/run_ko_shorts_target_wav_batch_v1.py"
DRIFT_KPI = ROOT / "scripts/build_ko_shorts_timing_drift_kpi_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _run_step(name: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    tail_lines = (proc.stdout or proc.stderr or "").strip().splitlines()
    tail = tail_lines[-1] if tail_lines else ""
    step: dict[str, Any] = {"step": name, "exit_code": proc.returncode, "cmd": cmd, "tail": tail}
    try:
        step["summary"] = json.loads(tail)
    except Exception:
        if proc.stderr:
            step["stderr_tail"] = proc.stderr.strip()[-400:]
    return step


def _python_for_alignment() -> str:
    if ALIGN_VENV_PY.is_file():
        return str(ALIGN_VENV_PY)
    return "py"


def build_alignment_spike_cmds(
    *,
    alignment_backend: str,
    routing_sidecar: str | None = None,
    include_whisperx: bool = False,
) -> list[tuple[str, list[str]]]:
    py = _python_for_alignment()
    spike_cmd = [
        py,
        str(ALIGN_SPIKE),
        "--cases",
        "clinical_sim",
        "--alignment-backend",
        alignment_backend,
    ]
    if routing_sidecar:
        spike_cmd.extend(["--routing-sidecar", routing_sidecar])
    if alignment_backend == "bench_all" and include_whisperx:
        spike_cmd.append("--include-whisperx")
    if alignment_backend == "bench_all":
        spike_cmd.append("--include-stable-ts")
    decision_cmd = ["py", str(SEG_DECISION), "--alignment-spike", ALIGN_SPIKE_OUT]
    return [
        ("alignment_backend_spike", spike_cmd),
        ("segment_backend_decision", decision_cmd),
    ]


def build_full_chain_plan(
    *,
    skip_fetch: bool,
    skip_spike: bool,
    skip_burn: bool,
    profile: str,
    include_tts_bench: bool,
    include_alignment_spike: bool,
    alignment_backend: str,
    routing_sidecar: str | None,
    include_whisperx: bool,
    port: int,
    include_delegate: bool = False,
    include_drift_kpi: bool = False,
) -> list[tuple[str, list[str]]]:
    steps: list[tuple[str, list[str]]] = []
    if not skip_fetch:
        steps.append(("fetch_clinical_sim", ["py", str(FETCH), "--source", "clinical_sim"]))
    if not skip_spike:
        compare_cases = "all" if include_tts_bench else "clinical_sim"
        compare_cmd = ["py", str(TIMING_COMPARE), "--cases", compare_cases]
        if skip_fetch:
            compare_cmd.append("--skip-fetch")
        steps.append(("timing_compare_spike", compare_cmd))
    if include_alignment_spike:
        steps.extend(
            build_alignment_spike_cmds(
                alignment_backend=alignment_backend,
                routing_sidecar=routing_sidecar,
                include_whisperx=include_whisperx,
            )
        )
    steps.extend(
        [
            ("gate_bench", ["py", str(GATE_BENCH)]),
            (
                "burnin_batch",
                ["py", str(BURNIN_BATCH), "--profile", profile] + (["--skip-burn"] if skip_burn else []),
            ),
            ("cursor_ide_qa", ["py", str(CURSOR_QA), "--port", str(port)]),
            ("manual_qa_checklist", ["py", str(QA_CHECKLIST)]),
        ]
    )
    if include_delegate:
        steps.append(
            (
                "target_wav_delegate",
                ["py", str(TARGET_WAV_BATCH), "--delegate-only", "--no-refetch", "--profile", profile],
            )
        )
    if include_drift_kpi:
        steps.append(("timing_drift_kpi", ["py", str(DRIFT_KPI)]))
    return steps


def run_full_chain_v1(
    *,
    skip_fetch: bool = False,
    skip_spike: bool = False,
    skip_burn: bool = False,
    profile: str = "netflix_v16",
    include_tts_bench: bool = False,
    include_alignment_spike: bool = False,
    alignment_backend: str = MODE_AUTO,
    routing_sidecar: str | None = None,
    include_whisperx: bool = False,
    port: int = 8796,
    include_delegate: bool = False,
    include_drift_kpi: bool = False,
) -> dict[str, Any]:
    plan = build_full_chain_plan(
        skip_fetch=skip_fetch,
        skip_spike=skip_spike,
        skip_burn=skip_burn,
        profile=profile,
        include_tts_bench=include_tts_bench,
        include_alignment_spike=include_alignment_spike,
        alignment_backend=alignment_backend,
        routing_sidecar=routing_sidecar,
        include_whisperx=include_whisperx,
        port=port,
        include_delegate=include_delegate,
        include_drift_kpi=include_drift_kpi,
    )
    results: list[dict[str, Any]] = []
    ok = True
    for name, cmd in plan:
        step = _run_step(name, cmd)
        results.append(step)
        ok = ok and step["exit_code"] == 0

    cursor_summary = next((s.get("summary") for s in results if s["step"] == "cursor_ide_qa"), None) or {}
    return {
        "schema": "ko_shorts_full_chain_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "profile": profile,
        "include_tts_bench": include_tts_bench,
        "include_alignment_spike": include_alignment_spike,
        "alignment_backend": alignment_backend,
        "routing_sidecar": routing_sidecar,
        "include_whisperx": include_whisperx,
        "ok": ok,
        "step_count": len(results),
        "steps": results,
        "cursor_qa_auto_pass": cursor_summary.get("ok"),
        "preview_url": cursor_summary.get("preview_url"),
        "artifacts": {
            "manifest": "reports/ko_shorts_clinical_sim_manifest_v1_latest.json",
            "timing_compare": "reports/ko_shorts_timing_compare_v1_latest.json",
            "gate_bench": "reports/ko_shorts_subtitle_gate_bench_v1_latest.json",
            "burnin_batch": "reports/ko_shorts_burnin_batch_v1_latest.json",
            "cursor_qa": "reports/ko_shorts_cursor_ide_qa_v1_latest.json",
            "preview_html": "reports/ko_shorts_cursor_preview_v1.html",
            "alignment_spike": ALIGN_SPIKE_OUT,
            "segment_decision": "reports/ko_shorts_segment_backend_decision_v1_latest.json",
            "target_wav_batch": "reports/ko_shorts_target_wav_batch_v1_latest.json",
            "timing_drift_kpi": "reports/ko_shorts_timing_drift_kpi_v1_latest.json",
        },
        "include_delegate": include_delegate,
        "include_drift_kpi": include_drift_kpi,
        "reproduce": "py scripts/run_ko_shorts_full_chain_v1.py --include-alignment-spike --alignment-backend auto --include-delegate --include-drift-kpi",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--profile", default="netflix_v16")
    ap.add_argument("--port", type=int, default=8796)
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--skip-spike", action="store_true", help="skip whisper spike / timing compare")
    ap.add_argument("--skip-burn", action="store_true")
    ap.add_argument("--include-tts-bench", action="store_true")
    ap.add_argument(
        "--include-alignment-spike",
        action="store_true",
        help="bench faster-whisper vs stable-ts (+ optional whisperx) after spike",
    )
    ap.add_argument(
        "--include-whisperx",
        action="store_true",
        help="with --alignment-backend bench_all only",
    )
    ap.add_argument(
        "--alignment-backend",
        default=MODE_AUTO,
        help="auto (default) | faster_whisper | whisperx | stable_ts | bench_all",
    )
    ap.add_argument("--routing-sidecar", default=None, help="JSON sidecar for domain_hint / override")
    ap.add_argument(
        "--quick",
        action="store_true",
        help="skip fetch+spike; reuse existing WAV/spike artifacts",
    )
    ap.add_argument(
        "--include-delegate",
        action="store_true",
        help="after core chain run delegated custom WAV batch (--delegate-only)",
    )
    ap.add_argument(
        "--include-drift-kpi",
        action="store_true",
        help="aggregate P0-P1 drift KPI from spike artifacts",
    )
    args = ap.parse_args()

    skip_fetch = args.skip_fetch or args.quick
    skip_spike = args.skip_spike or args.quick

    report = run_full_chain_v1(
        skip_fetch=skip_fetch,
        skip_spike=skip_spike,
        skip_burn=args.skip_burn,
        profile=args.profile,
        include_tts_bench=args.include_tts_bench,
        include_alignment_spike=args.include_alignment_spike,
        alignment_backend=args.alignment_backend,
        routing_sidecar=args.routing_sidecar,
        include_whisperx=args.include_whisperx,
        port=args.port,
        include_delegate=args.include_delegate,
        include_drift_kpi=args.include_drift_kpi,
    )
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": report["ok"],
                "out": _rel(out),
                "preview_url": report.get("preview_url"),
                "step_count": report["step_count"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
