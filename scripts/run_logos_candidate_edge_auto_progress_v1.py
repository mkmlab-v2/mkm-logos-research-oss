#!/usr/bin/env python3
"""Auto-loop recommended wave until net-new batch is empty ([HYPO] B-track)."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WAVE = ROOT / "scripts/run_logos_candidate_edge_recommended_wave_v1.py"
REVIEW_DECISIONS = ROOT / "scripts/apply_logos_candidate_edge_human_review_decisions_v1.py"
MAINTENANCE = ROOT / "scripts/run_logos_candidate_edge_post_saturation_maintenance_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_candidate_edge_auto_progress_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_wave(*, skip_triage: bool, skip_ann: bool) -> tuple[int, dict[str, Any]]:
    cmd = [sys.executable, str(WAVE)]
    if skip_triage:
        cmd.append("--skip-triage")
    if skip_ann:
        cmd.append("--skip-ann-lite-merge")
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False, timeout=3600)
    wave_path = ROOT / "docs/final/artifacts/logos_candidate_edge_recommended_wave_v1_latest.json"
    doc: dict[str, Any] = {}
    if wave_path.is_file():
        try:
            doc = json.loads(wave_path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            pass
    return int(proc.returncode), doc


def _reapprove_ann_lite() -> tuple[int, str]:
    proc = subprocess.run(
        [
            sys.executable,
            str(REVIEW_DECISIONS),
            "--auto-approve-ann-lite-primary",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    out = (proc.stdout or proc.stderr or "").strip()
    return int(proc.returncode), out[-300:] if len(out) > 300 else out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--max-iterations", type=int, default=5)
    ap.add_argument(
        "--refresh-triage",
        action="store_true",
        help="Run triage on iteration 1 (resets queue); re-approves ann_lite after",
    )
    ap.add_argument("--skip-maintenance", action="store_true")
    ap.add_argument("--chain-out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    iterations: list[dict[str, Any]] = []
    exit_code = 0
    total_appended = 0
    post_steps: list[dict[str, Any]] = []

    for i in range(1, max(1, int(args.max_iterations)) + 1):
        skip_triage = not args.refresh_triage or i > 1
        code, wave_doc = _run_wave(skip_triage=skip_triage, skip_ann=True)
        if args.refresh_triage and i == 1 and code == 0:
            ra_code, ra_tail = _reapprove_ann_lite()
            post_steps.append({"step": "reapprove_ann_lite_after_triage", "exit_code": ra_code, "tail": ra_tail})
            if ra_code != 0:
                code = ra_code
        batch = wave_doc.get("netnew_batch") or {}
        selected = int(batch.get("selected") or 0)
        appended = int(batch.get("merge_appended") or 0)
        edges = (wave_doc.get("canonical_graph") or {}).get("edges_line_count")
        iterations.append(
            {
                "iteration": i,
                "exit_code": code,
                "netnew_selected": selected,
                "merge_appended": appended,
                "edges_line_count": edges,
            }
        )
        total_appended += appended
        if code != 0:
            exit_code = code
            break
        if selected == 0 or appended == 0:
            break

    saturation = bool(iterations and (iterations[-1].get("netnew_selected") or 0) == 0)
    maintenance_doc: dict[str, Any] = {}
    if saturation and not args.skip_maintenance and exit_code == 0:
        proc = subprocess.run(
            [sys.executable, str(MAINTENANCE)],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            check=False,
            timeout=3600,
        )
        post_steps.append(
            {
                "step": "post_saturation_maintenance",
                "exit_code": int(proc.returncode),
                "tail": (proc.stdout or proc.stderr or "")[-400:],
            }
        )
        maint_path = ROOT / "docs/final/artifacts/logos_candidate_edge_post_saturation_maintenance_v1_latest.json"
        if maint_path.is_file():
            try:
                maintenance_doc = json.loads(maint_path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                pass
        if proc.returncode != 0:
            exit_code = int(proc.returncode)

    doc = {
        "schema": "logos_candidate_edge_auto_progress_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "iterations_run": len(iterations),
        "total_appended": total_appended,
        "exit_code": exit_code,
        "iterations": iterations,
        "saturation_reached": saturation,
        "post_steps": post_steps,
        "maintenance": {
            "gold_required_all_pass": maintenance_doc.get("gold_required_all_pass"),
            "l9_l12_ok": maintenance_doc.get("l9_l12_ok"),
            "queue_stats": maintenance_doc.get("queue_stats"),
        },
    }
    out_path = args.chain_out if args.chain_out.is_absolute() else ROOT / args.chain_out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": exit_code == 0, "iterations": len(iterations), "total_appended": total_appended, "out": str(out_path)}))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
