#!/usr/bin/env python3
"""
HP sweep for dynamic BGM conditioning (B-track [HYPO]).

Builds conditioning diffs across hp_pct grid; optionally runs MusicGen melody chain
per point and aggregates gate outcomes into a comparison artifact.

Track C research only — not live game wiring.
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

try:
    from scripts.build_dynamic_bgm_conditioning_diff_v1 import apply_patch_to_conditioning, build_dynamic_diff
except ModuleNotFoundError:
    sys.path.insert(0, str(ROOT))
    from scripts.build_dynamic_bgm_conditioning_diff_v1 import apply_patch_to_conditioning, build_dynamic_diff


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_hp_values(raw: str) -> list[float]:
    out: list[float] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        out.append(max(0.0, min(1.0, float(part))))
    return out or [0.2, 0.5, 0.85, 1.0]


def _parse_lens_counts(raw: str) -> list[int]:
    out: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        n = int(part)
        if n not in (0, 1, 3):
            raise ValueError(f"lens_count must be 0, 1, or 3; got {n}")
        if n not in out:
            out.append(n)
    return out or [1]


def _build_base_conditioning(seed_json: Path, out_path: Path) -> dict[str, Any]:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    rc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_sasang_music_conditioning_from_seed_v1.py"),
            "--seed-json",
            str(seed_json.resolve()),
            "--out-json",
            str(out_path.resolve()),
        ],
        cwd=str(ROOT),
    ).returncode
    if rc != 0:
        raise RuntimeError(f"build base conditioning failed exit={rc}")
    return _load_json(out_path)


def _predict_lens_risk(tempo_bpm: float, *, seed_bpm: float = 96.0) -> dict[str, Any]:
    """Heuristic: MusicGen often reads ~180 BPM; harmonic half vs conditioning target."""
    from scripts.audio.musicgen_numeric_conditioning_v1 import clamp_tempo_for_lens_gate

    observed = 180.0
    half = 90.0
    effective_tempo, clamp_meta = clamp_tempo_for_lens_gate(tempo_bpm)
    delta_full = abs(observed - effective_tempo) / max(effective_tempo, 1e-9) * 100.0
    delta_half = abs(half - effective_tempo) / max(effective_tempo, 1e-9) * 100.0
    delta_seed_half = abs(half - seed_bpm) / max(seed_bpm, 1e-9) * 100.0
    best = min(delta_full, delta_half)
    return {
        "predicted_bpm_observed_harmonic": half,
        "predicted_bpm_delta_pct_vs_target": round(best, 4),
        "predicted_lens_pass_at_12pct": best <= 12.0,
        "reference_seed_bpm_harmonic_delta": round(delta_seed_half, 4),
        "lens_safe_tempo_clamp": clamp_meta,
        "effective_tempo_bpm_target": effective_tempo,
    }


def _run_chain(hp: float, args: argparse.Namespace, out_root: Path) -> dict[str, Any]:
    tag = f"hp{int(round(hp * 100)):03d}"
    chain_dir = out_root / tag
    demo_path = chain_dir / "_point_demo.json"
    cmd = [
        sys.executable,
        str(ROOT / "scripts/run_dynamic_bgm_melody_chain_v1.py"),
        "--seed-json",
        str(args.seed_json.resolve()),
        "--hp-pct",
        str(hp),
        "--sasang",
        args.sasang,
        "--output-dir",
        str(chain_dir),
        "--gate-track",
        args.gate_track,
        "--placeholder-seconds",
        str(args.placeholder_seconds),
        "--numeric-mode",
        args.numeric_mode,
        "--demo-report-json",
        str(demo_path),
    ]
    if args.two_pass:
        cmd.append("--two-pass")
    rc = subprocess.run(cmd, cwd=str(ROOT)).returncode
    row: dict[str, Any] = {"hp_pct": hp, "chain_exit_code": rc, "chain_dir": str(chain_dir.as_posix())}
    if demo_path.is_file():
        demo = _load_json(demo_path)
        row["gate_decision"] = demo.get("gate", {}).get("decision")
        row["run_id"] = demo.get("generation", {}).get("run_id")
        row["tempo_bpm_target"] = demo.get("conditioning", {}).get("tempo_bpm_target")
        row["velocity_0_1"] = demo.get("conditioning", {}).get("velocity_0_1")
        row["gate_metrics"] = demo.get("gate", {}).get("metrics")
        row["wav_path"] = demo.get("generation", {}).get("wav_path")
    return row


# Prior runs (import without re-GPU when sweep dir missing gate)
_KNOWN_RUNS: dict[float, dict[str, Any]] = {
    0.2: {
        "run_id": "63cf89ab734848b3",
        "gate_decision": "PASS",
        "tempo_bpm_target": 102.27,
        "gate_report": "reports/audio/audio_gate_63cf89ab734848b3_000.json",
        "source": "counsel_audio_regen_hp020_v2_lens_clamp",
    },
    0.5: {
        "run_id": "c5e2e10494e24a0b",
        "gate_decision": "PASS",
        "tempo_bpm_target": 101.76,
        "gate_report": "reports/audio/audio_gate_c5e2e10494e24a0b_000.json",
        "source": "hp_sweep_gen_hp050",
    },
    0.85: {
        "run_id": "7880ab7f8ac94b0a",
        "gate_decision": "PASS",
        "tempo_bpm_target": 96.0,
        "gate_report": "reports/audio/audio_gate_7880ab7f8ac94b0a_000.json",
        "source": "numeric_melody_poc_96",
    },
    1.0: {
        "run_id": "21989d15083d422a",
        "gate_decision": "PASS",
        "tempo_bpm_target": 96.0,
        "gate_report": "reports/audio/audio_gate_21989d15083d422a_000.json",
        "source": "dynamic_bgm_chain_hp100",
    },
}


def main() -> int:
    ap = argparse.ArgumentParser(description="Dynamic BGM hp_pct sweep aggregator.")
    ap.add_argument("--seed-json", type=Path, default=Path("data/audio/seeds/tension_sasang_01.example.json"))
    ap.add_argument("--hp-values", type=str, default="0.2,0.5,0.85,1.0")
    ap.add_argument("--lens-counts", type=str, default="1", help="Charter R3 grid: 0,1,3 (comma-separated).")
    ap.add_argument("--export-grid-json", type=Path, default=Path("docs/final/artifacts/dynamic_bgm_lens_count_grid_v1_latest.json"))
    ap.add_argument("--sasang", type=str, default="soyang")
    ap.add_argument("--output-dir", type=Path, default=Path("workspace/audio_raw_economy/_dynamic_bgm_hp_sweep"))
    ap.add_argument("--export-json", type=Path, default=Path("docs/final/artifacts/dynamic_bgm_hp_sweep_v1_latest.json"))
    ap.add_argument("--gate-track", choices=("A", "B"), default="B")
    ap.add_argument("--placeholder-seconds", type=float, default=8.0)
    ap.add_argument("--numeric-mode", choices=("melody", "stretch", "off"), default="melody")
    ap.add_argument("--two-pass", action="store_true")
    ap.add_argument("--conditioning-only", action="store_true", help="Skip GPU; diff + lens risk heuristic only.")
    ap.add_argument("--run-generate", action="store_true", help="Run melody chain for points without fresh gate.")
    ap.add_argument("--import-known", action="store_true", default=True, help="Fill from prior PoC run_ids when missing.")
    ap.add_argument("--no-import-known", action="store_false", dest="import_known")
    args = ap.parse_args()

    seed_abs = args.seed_json.resolve()
    if not seed_abs.is_file():
        print(json.dumps({"ok": False, "error": "seed-json missing"}))
        return 2

    hp_values = _parse_hp_values(args.hp_values)
    try:
        lens_counts = _parse_lens_counts(args.lens_counts)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    out_root = args.output_dir.resolve()
    out_root.mkdir(parents=True, exist_ok=True)

    base_path = out_root / "base_conditioning.json"
    base_cond = _build_base_conditioning(seed_abs, base_path)

    rows: list[dict[str, Any]] = []
    for lens_count in lens_counts:
        for hp in hp_values:
            tag = f"lc{lens_count}_hp{int(round(hp * 100)):03d}"
            diff = build_dynamic_diff(
                base_conditioning=base_cond,
                hp_pct=hp,
                sasang=args.sasang or None,
                lens_count=lens_count,
            )
            merged = apply_patch_to_conditioning(base_cond, diff)
            diff_path = out_root / f"{tag}.diff.json"
            cond_path = out_root / f"{tag}.conditioning.json"
            diff_path.write_text(json.dumps(diff, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            cond_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

            tempo = float(merged.get("conditioning", {}).get("tempo_bpm_target") or 0)
            row: dict[str, Any] = {
                "lens_count": lens_count,
                "active_lenses": diff.get("inputs", {}).get("active_lenses") or [],
                "hp_pct": hp,
                "sasang": diff.get("inputs", {}).get("sasang"),
                "mood": diff.get("inputs", {}).get("mood"),
                "tempo_bpm_target": tempo,
                "velocity_0_1": merged.get("conditioning", {}).get("velocity_0_1"),
                "conditioning_path": str(cond_path.as_posix()),
                "diff_path": str(diff_path.as_posix()),
                "lens_risk_heuristic": _predict_lens_risk(tempo),
            }

            if args.import_known and lens_count == 1 and hp in _KNOWN_RUNS:
                known = _KNOWN_RUNS[hp]
                rep = ROOT / known["gate_report"]
                if rep.is_file():
                    gate_doc = _load_json(rep)
                    row["gate_decision"] = gate_doc.get("decision")
                    row["run_id"] = known["run_id"]
                    row["gate_metrics"] = gate_doc.get("metrics")
                    row["import_source"] = known["source"]

            if args.run_generate and not args.conditioning_only:
                chain_row = _run_chain(hp, args, out_root)
                row.update({k: v for k, v in chain_row.items() if v is not None})

            rows.append(row)

    pass_n = sum(1 for r in rows if r.get("gate_decision") == "PASS")
    fail_n = sum(1 for r in rows if r.get("gate_decision") == "FAIL")

    doc = {
        "schema": "dynamic_bgm_hp_sweep_v1",
        "version": "1.1.0" if len(lens_counts) > 1 or lens_counts != [1] else "1.0.0",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now_iso(),
        "track_wall": "B_track_research_only",
        "seed_json": str(seed_abs.as_posix()),
        "sasang": args.sasang,
        "lens_counts": lens_counts,
        "numeric_mode": args.numeric_mode if not args.conditioning_only else "conditioning_only",
        "summary": {
            "points": len(rows),
            "lens_count_grid": lens_counts,
            "gate_pass": pass_n,
            "gate_fail": fail_n,
            "gate_unknown": len(rows) - pass_n - fail_n,
            "insight": "lens_safe_tempo_clamp on dynamic diff; BPM stretch alone does not move detector off ~180 — clamp target to harmonic-safe band.",
        },
        "rows": rows,
        "track_c_audio_hook_bullets": [
            "Functional BGM: hp_pct + sasang → conditioning diff → self-hosted MusicGen + gate JSON",
            "Suno complement (not competitor): audit trail + Apache2 weights · no vocal pop claims",
            "Demo SSOT: dynamic_bgm_melody_chain_demo_v1_latest.json + this sweep table",
            "[HYPO] research_only — legal send HOLD until counsel sign-off",
        ],
        "demo_pointer": "docs/final/artifacts/dynamic_bgm_melody_chain_demo_v1_latest.json",
        "disclaimer": "lens_risk_heuristic assumes observed~180/half~90; operational gate uses measured WAV.",
    }

    args.export_json.parent.mkdir(parents=True, exist_ok=True)
    args.export_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_root / "_hp_sweep_summary.json").write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if len(lens_counts) > 1:
        grid_doc = {
            "schema": "dynamic_bgm_lens_count_grid_v1",
            "version": "1.0.0",
            "hypothesis_class": "HYPO",
            "charter_ref": "LENS_UTILIZATION_CHARTER_V1 R3",
            "generated_at_utc": _utc_now_iso(),
            "track_wall": "B_track_research_only",
            "lens_counts": lens_counts,
            "hp_values": hp_values,
            "rows": rows,
            "summary": {
                "grid_points": len(rows),
                "by_lens_count": {
                    str(lc): sum(1 for r in rows if r.get("lens_count") == lc) for lc in lens_counts
                },
            },
            "sweep_pointer": str(args.export_json.as_posix()),
            "disclaimer": "[HYPO] lens_count ablation on conditioning diff only; gate metrics imported for lc=1 baseline.",
        }
        args.export_grid_json.parent.mkdir(parents=True, exist_ok=True)
        args.export_grid_json.write_text(json.dumps(grid_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "ok": True,
                "export_json": str(args.export_json),
                "export_grid_json": str(args.export_grid_json) if len(lens_counts) > 1 else None,
                "points": len(rows),
                "lens_counts": lens_counts,
                "gate_pass": pass_n,
                "gate_fail": fail_n,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
