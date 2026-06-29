#!/usr/bin/env python3
"""
Apply sasang_music_conditioning_feedback_v1 patch onto pass-1 conditioning (pass-2 adapter).

B-track [HYPO] — does not mutate seed JSON or auto-promote Track A.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from pathlib import Path
from typing import Any


def apply_feedback_patch(
    conditioning: dict[str, Any],
    feedback: dict[str, Any],
    *,
    pass_label: str = "pass2",
) -> dict[str, Any]:
    if feedback.get("schema") != "sasang_music_conditioning_feedback_v1":
        raise ValueError("feedback schema must be sasang_music_conditioning_feedback_v1")
    if conditioning.get("schema") != "sasang_music_conditioning_v1":
        raise ValueError("conditioning schema must be sasang_music_conditioning_v1")

    patch = feedback.get("suggested_conditioning_patch") or {}
    out = copy.deepcopy(conditioning)
    cond = out.setdefault("conditioning", {})

    if patch.get("tempo_bpm_target") is not None:
        cond["tempo_bpm_target"] = float(patch["tempo_bpm_target"])

    if patch.get("prompt_en_hint"):
        cond["prompt_en"] = str(patch["prompt_en_hint"])
    elif patch.get("tempo_bpm_target") is not None and cond.get("prompt_en"):
        bpm = int(round(float(patch["tempo_bpm_target"])))
        cond["prompt_en"] = re.sub(
            r"\b\d+\s*bpm\b",
            f"{bpm} bpm",
            str(cond["prompt_en"]),
            count=1,
            flags=re.I,
        )

    if patch.get("duration_seconds") is not None:
        cond["duration_seconds"] = float(patch["duration_seconds"])

    run_id = str(feedback.get("run_id") or "unknown")
    gate_decision = str(feedback.get("gate_decision") or "")
    prior_notes = str(out.get("notes") or "").strip()
    audit = f"{pass_label}: feedback run_id={run_id} gate={gate_decision}"
    if patch.get("bpm_delta_pct_after_patch") is not None:
        audit += f" bpm_delta_after_patch={patch['bpm_delta_pct_after_patch']}"
    if patch.get("last_lufs_integrated") is not None:
        audit += f" lufs={patch['last_lufs_integrated']}"
    out["notes"] = f"{prior_notes}\n{audit}".strip() if prior_notes else audit

    prov = out.setdefault("provenance", {})
    base_exp = str(prov.get("experiment_id") or "adapter")
    prov["experiment_id"] = f"{base_exp}_{pass_label}_{run_id[:8]}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Merge conditioning feedback patch for pass-2 generation.")
    ap.add_argument("--conditioning-json", type=Path, required=True)
    ap.add_argument("--feedback-json", type=Path, required=True)
    ap.add_argument("--out-json", type=Path, required=True)
    ap.add_argument("--pass-label", type=str, default="pass2")
    args = ap.parse_args()

    for label, path in (("conditioning-json", args.conditioning_json), ("feedback-json", args.feedback_json)):
        if not path.is_file():
            print(json.dumps({"ok": False, "error": f"{label} missing", "path": str(path)}))
            return 2

    conditioning = json.loads(args.conditioning_json.read_text(encoding="utf-8"))
    feedback = json.loads(args.feedback_json.read_text(encoding="utf-8"))
    merged = apply_feedback_patch(conditioning, feedback, pass_label=args.pass_label)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "out": str(args.out_json),
                "tempo_bpm_target": merged.get("conditioning", {}).get("tempo_bpm_target"),
                "feedback_run_id": feedback.get("run_id"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
