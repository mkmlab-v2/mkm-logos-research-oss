#!/usr/bin/env python3
"""
Build sasang_music_conditioning_feedback_v1 from gate report + upstream conditioning.

B-track [HYPO] — closed-loop hint for the next adapter/generation pass (not auto-promotion).
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.audio.detect_bpm_v1 import bpm_delta_pct
except ModuleNotFoundError:
    from detect_bpm_v1 import bpm_delta_pct


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _best_bpm_candidate(observed: float, target: float) -> tuple[float, float]:
    candidates = [
        (observed, bpm_delta_pct(observed, target)),
        (observed / 2.0, bpm_delta_pct(observed / 2.0, target)) if observed >= 2.0 else (observed, 999.0),
        (observed * 2.0, bpm_delta_pct(observed * 2.0, target)),
    ]
    best_bpm, best_delta = min(candidates, key=lambda row: row[1])
    return best_bpm, best_delta


def build_feedback(
    *,
    gate_report: dict[str, Any],
    conditioning: dict[str, Any] | None,
    gate_report_path: Path,
    conditioning_path: Path | None,
) -> dict[str, Any]:
    metrics = gate_report.get("metrics") or {}
    cond = (conditioning or {}).get("conditioning") or {}
    target_bpm = float(cond.get("tempo_bpm_target") or gate_report.get("seed_bpm") or 0)
    observed = metrics.get("bpm_observed")
    lufs = metrics.get("lufs_integrated")

    patch: dict[str, Any] = {}
    notes: list[str] = []

    if observed is not None and target_bpm > 0:
        best_bpm, best_delta = _best_bpm_candidate(float(observed), target_bpm)
        patch["tempo_bpm_target"] = round(best_bpm, 2)
        patch["prior_tempo_bpm_target"] = target_bpm
        patch["bpm_delta_pct_after_patch"] = round(best_delta, 4)
        if abs(float(observed) - best_bpm) > 0.5:
            notes.append(f"harmonic_fold: observed={observed} -> candidate={best_bpm}")
        if best_delta <= 12.0:
            notes.append("bpm_within_gate_tolerance_after_patch")
        else:
            notes.append("bpm_still_outside_tolerance_consider_prompt_or_seed_edit")

    if lufs is not None:
        patch["last_lufs_integrated"] = float(lufs)

    duration = cond.get("duration_seconds")
    if duration is not None:
        patch["duration_seconds"] = float(duration)

    if patch.get("tempo_bpm_target") is not None and cond.get("prompt_en"):
        bpm = int(round(float(patch["tempo_bpm_target"])))
        base_prompt = str(cond.get("prompt_en"))
        import re

        if re.search(r"\b\d+\s*bpm\b", base_prompt, flags=re.I):
            patch["prompt_en_hint"] = re.sub(r"\b\d+\s*bpm\b", f"{bpm} bpm", base_prompt, count=1, flags=re.I)
        else:
            patch["prompt_en_hint"] = f"{base_prompt}, {bpm} bpm"

    return {
        "schema": "sasang_music_conditioning_feedback_v1",
        "version": "1.0.0",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now_iso(),
        "run_id": str(gate_report.get("run_id") or ""),
        "gate_decision": str(gate_report.get("decision") or ""),
        "artifacts": {
            "gate_report_path": str(gate_report_path.as_posix()),
            "conditioning_path": str(conditioning_path.as_posix()) if conditioning_path else None,
        },
        "observed": {
            "bpm": observed,
            "bpm_delta_pct": metrics.get("bpm_delta_pct"),
            "lufs_integrated": lufs,
            "loop_seamlessness_pass": metrics.get("loop_seamlessness_pass"),
            "lufs_target_match": metrics.get("lufs_target_match"),
            "lens_alignment_pass": metrics.get("lens_alignment_pass"),
        },
        "suggested_conditioning_patch": patch,
        "notes": notes,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Build conditioning feedback JSON from gate report.")
    ap.add_argument("--gate-report", type=Path, required=True)
    ap.add_argument("--conditioning-json", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, required=True)
    args = ap.parse_args()

    if not args.gate_report.is_file():
        print(json.dumps({"ok": False, "error": "gate-report missing"}))
        return 2

    gate = json.loads(args.gate_report.read_text(encoding="utf-8"))
    conditioning = None
    cond_path = args.conditioning_json
    if cond_path and cond_path.is_file():
        conditioning = json.loads(cond_path.read_text(encoding="utf-8"))

    doc = build_feedback(
        gate_report=gate,
        conditioning=conditioning,
        gate_report_path=args.gate_report,
        conditioning_path=cond_path,
    )
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(args.out_json)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
