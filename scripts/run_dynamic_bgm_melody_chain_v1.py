#!/usr/bin/env python3
"""
Dynamic BGM end-to-end chain (B-track [HYPO]).

seed -> base conditioning -> hp_pct/sasang diff -> MusicGen numeric melody -> gate
-> optional two-pass when pass-1 gate PASS + feedback sidecar exists.

Track C demo / research only — not live game wiring or Track A promotion.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

try:
    from scripts.build_dynamic_bgm_conditioning_diff_v1 import apply_patch_to_conditioning, build_dynamic_diff
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from scripts.build_dynamic_bgm_conditioning_diff_v1 import apply_patch_to_conditioning, build_dynamic_diff


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path | None = None) -> int:
    print(json.dumps({"step": cmd[1] if len(cmd) > 1 else cmd[0], "cmd": cmd}, ensure_ascii=False), flush=True)
    return subprocess.run(cmd, cwd=str(cwd or ROOT)).returncode


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _latest_gate_report(gate_dir: Path, run_id: str) -> Path | None:
    candidate = gate_dir / f"audio_gate_{run_id}_000.json"
    if candidate.is_file():
        return candidate
    rep = ROOT / "reports" / "audio" / f"audio_gate_{run_id}_000.json"
    return rep if rep.is_file() else None


def _find_batch_run_id(batch_dir: Path) -> str | None:
    summaries = sorted(batch_dir.glob("_batch_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not summaries:
        return None
    try:
        doc = _load_json(summaries[0])
        return str(doc.get("run_id") or "")
    except Exception:
        return None


def build_plan(args: argparse.Namespace) -> dict[str, Any]:
    out = args.output_dir.resolve()
    return {
        "base_conditioning": str(out / "base_conditioning.json"),
        "dynamic_diff": str(out / f"hp{int(args.hp_pct * 100):03d}.diff.json"),
        "dynamic_conditioning": str(out / f"hp{int(args.hp_pct * 100):03d}.conditioning.json"),
        "batch_dir": str(out / "gen"),
        "demo_report": str(args.demo_report_json or out / "_dynamic_bgm_chain_demo.json"),
        "two_pass_dir": str(out / "two_pass") if args.two_pass else None,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Dynamic hp_pct -> melody MusicGen chain (B-track [HYPO]).")
    ap.add_argument("--seed-json", type=Path, required=True)
    ap.add_argument("--hp-pct", type=float, required=True, help="0=low HP/tense, 1=full HP/calm")
    ap.add_argument("--sasang", type=str, default="")
    ap.add_argument("--output-dir", type=Path, default=Path("workspace/audio_raw_economy/_dynamic_bgm_chain"))
    ap.add_argument("--gate-track", choices=("A", "B"), default="B")
    ap.add_argument("--placeholder-seconds", type=float, default=8.0)
    ap.add_argument("--numeric-mode", choices=("melody", "stretch", "off"), default="melody")
    ap.add_argument("--two-pass", action="store_true", help="Run two-pass adapter when pass-1 gate PASS.")
    ap.add_argument("--demo-report-json", type=Path, default=None)
    ap.add_argument("--dry-run-plan", action="store_true")
    args = ap.parse_args()

    seed_abs = args.seed_json.resolve()
    if not seed_abs.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    out_root = args.output_dir.resolve()
    plan = build_plan(args)
    if args.dry_run_plan:
        print(json.dumps({"ok": True, "dry_run_plan": plan, "hp_pct": args.hp_pct}, indent=2, ensure_ascii=False))
        return 0

    external = (os.environ.get("MKM_AUDIO_EXTERNAL_SCRIPT") or "scripts/audio/musicgen_external_generator_v1.py").strip()
    if not external:
        print(json.dumps({"ok": False, "error": "MKM_AUDIO_EXTERNAL_SCRIPT missing"}))
        return 4

    out_root.mkdir(parents=True, exist_ok=True)
    base_cond_path = Path(plan["base_conditioning"])
    diff_path = Path(plan["dynamic_diff"])
    dyn_cond_path = Path(plan["dynamic_conditioning"])
    batch_dir = Path(plan["batch_dir"])

    cond_cmd = [
        sys.executable,
        str(ROOT / "scripts/build_sasang_music_conditioning_from_seed_v1.py"),
        "--seed-json",
        str(seed_abs),
        "--out-json",
        str(base_cond_path),
        "--max-duration-seconds",
        str(float(args.placeholder_seconds)),
    ]
    if args.sasang:
        cond_cmd.extend(["--sasang-primary", str(args.sasang).strip().lower()])
    rc = _run(cond_cmd)
    if rc != 0:
        return rc

    base_cond = _load_json(base_cond_path)
    diff = build_dynamic_diff(base_conditioning=base_cond, hp_pct=args.hp_pct, sasang=args.sasang or None)
    merged = apply_patch_to_conditioning(base_cond, diff)
    diff_path.write_text(json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    dyn_cond_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    os.environ["MKM_AUDIO_EXTERNAL_SCRIPT"] = external
    os.environ["MKM_AUDIO_CONDITIONING_JSON"] = str(dyn_cond_path)
    os.environ["MKM_AUDIO_MUSICGEN_NUMERIC_MODE"] = args.numeric_mode

    batch_cmd = [
        sys.executable,
        str(ROOT / "scripts/audio/run_bgm_generation_batch.py"),
        "--seed-json",
        str(seed_abs),
        "--emit",
        "external",
        "--count",
        "1",
        "--output-dir",
        str(batch_dir),
        "--run-gate",
        "--gate-track",
        args.gate_track,
        "--placeholder-seconds",
        str(args.placeholder_seconds),
    ]
    rc = _run(batch_cmd)
    batch_exit = rc

    run_id = _find_batch_run_id(batch_dir) or ""
    gate_path = _latest_gate_report(ROOT / "reports" / "audio", run_id) if run_id else None
    gate_doc: dict[str, Any] | None = _load_json(gate_path) if gate_path and gate_path.is_file() else None
    gate_decision = str((gate_doc or {}).get("decision") or "UNKNOWN")

    two_pass_summary: dict[str, Any] | None = None
    if args.two_pass and gate_decision == "PASS":
        tp_dir = Path(plan["two_pass_dir"] or (out_root / "two_pass"))
        tp_rc = _run(
            [
                sys.executable,
                str(ROOT / "scripts/run_sasang_music_two_pass_chain_v1.py"),
                "--seed-json",
                str(seed_abs),
                "--output-dir",
                str(tp_dir),
                "--gate-track",
                args.gate_track,
                "--pass1-conditioning-json",
                str(dyn_cond_path),
                "--pass1-feedback-json",
                str(batch_dir / f"bgm_{run_id}_000.conditioning_feedback.json"),
            ]
        )
        two_pass_summary = {"exit_code": tp_rc, "output_dir": str(tp_dir)}
        if tp_rc != 0:
            batch_exit = tp_rc

    wav_glob = list(batch_dir.glob("bgm_*.wav"))
    demo = {
        "schema": "dynamic_bgm_melody_chain_demo_v1",
        "version": "1.0.0",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now_iso(),
        "track_wall": "B_track_research_only",
        "inputs": {
            "seed_json": str(seed_abs.as_posix()),
            "hp_pct": args.hp_pct,
            "sasang": diff.get("inputs", {}).get("sasang"),
            "numeric_mode": args.numeric_mode,
        },
        "conditioning": {
            "base_path": str(base_cond_path.as_posix()),
            "diff_path": str(diff_path.as_posix()),
            "dynamic_path": str(dyn_cond_path.as_posix()),
            "tempo_bpm_target": merged.get("conditioning", {}).get("tempo_bpm_target"),
            "velocity_0_1": merged.get("conditioning", {}).get("velocity_0_1"),
        },
        "generation": {
            "run_id": run_id,
            "batch_dir": str(batch_dir.as_posix()),
            "wav_path": str(wav_glob[0].as_posix()) if wav_glob else None,
            "batch_exit_code": rc,
        },
        "gate": {
            "decision": gate_decision,
            "report_path": str(gate_path.as_posix()) if gate_path else None,
            "metrics": (gate_doc or {}).get("metrics"),
        },
        "two_pass": two_pass_summary,
        "track_c_demo_bullets": [
            "Suno complement: self-hosted MusicGen + mechanical gate JSON audit trail",
            "Runtime stub: hp_pct + sasang -> conditioning diff (not live game wiring)",
            "Numeric PoC: melody guide + optional BPM post-align — not parametric DAW control",
            "[HYPO] / research_only — no clinical efficacy or Track A promotion claim",
        ],
        "disclaimer": "Operational (post-processor included) B-track demo; raw model BPM alignment remains imperfect.",
    }

    demo_path = Path(plan["demo_report"])
    demo_path.parent.mkdir(parents=True, exist_ok=True)
    demo_path.write_text(json.dumps(demo, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary = {
        "ok": batch_exit == 0,
        "demo_report": str(demo_path),
        "gate_decision": gate_decision,
        "run_id": run_id,
        "tempo_bpm_target": merged.get("conditioning", {}).get("tempo_bpm_target"),
    }
    (out_root / "_chain_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if batch_exit == 0 else batch_exit


if __name__ == "__main__":
    raise SystemExit(main())
