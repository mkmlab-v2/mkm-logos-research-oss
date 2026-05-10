#!/usr/bin/env python3
"""Chain: lens_music_gematria_v1 symbolic outputs → safety pre-gate → evaluate_audio_gate (B-track demo).

Does not render audio from symbols. Optional placeholder WAV exercises mechanical gate with seed BPM
from the lens. Track defaults to B; pass provenance + commercial_terms_tag for PASS on copyright metric.

Exit: 0 full PASS, 1 audio gate FAIL (symbolic passed), 2 symbolic HOLD/invalid lens.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CHAIN_SCHEMA = "lens_music_gate_chain_v1"
CHAIN_VERSION = "1.0.0"


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_lens_envelope(doc: dict[str, Any]) -> None:
    if doc.get("schema") != "lens_music_gematria_v1":
        raise ValueError("expected lens envelope schema lens_music_gematria_v1")


def _resolve_outputs(doc: dict[str, Any]) -> dict[str, Any]:
    ro = doc.get("resolved_outputs")
    if not isinstance(ro, dict):
        raise ValueError("missing resolved_outputs")
    return ro


def evaluate_symbolic_safety(
    outputs: dict[str, Any],
    *,
    policy: str,
) -> tuple[str, dict[str, Any], list[str], list[str]]:
    """Returns decision, effective_outputs, reasons, clip_notes."""
    reasons: list[str] = []
    clip_notes: list[str] = []
    out = json.loads(json.dumps(outputs))  # deep copy

    dyn = dict(out.get("dynamics") or {})
    safety = out.get("safety") or {}
    vel = float(dyn.get("velocity_0_1", 0.0))
    cap = float(safety.get("max_velocity_0_1", 1.0))
    lo = float(safety.get("min_hz", 20.0))
    hi = float(safety.get("max_hz", 20000.0))

    if lo >= hi:
        return "HOLD", out, ["safety_band_invalid_min_hz_ge_max_hz"], []

    tb = dict(out.get("tempo_bpm") or {})
    t_tgt = float(tb.get("target", 120.0))
    t_min = float(tb.get("min", 20.0))
    t_max = float(tb.get("max", 300.0))
    if t_tgt < t_min or t_tgt > t_max:
        reasons.append("tempo_target_outside_min_max_window")

    if vel > cap:
        if policy == "clip":
            dyn["velocity_0_1"] = cap
            out["dynamics"] = dyn
            clip_notes.append(f"velocity_clipped_from_{vel:g}_to_{cap:g}")
        else:
            reasons.append(f"velocity_over_cap_{vel:g}>{cap:g}")

    decision = "PASS"
    if reasons:
        decision = "HOLD"
    elif clip_notes:
        decision = "CLIPPED_OK"
    out["dynamics"] = dyn
    out["tempo_bpm"] = tb
    return decision, out, reasons, clip_notes


def build_seed_from_outputs(outputs: dict[str, Any], *, seed_prefix: str) -> dict[str, Any]:
    tb = outputs["tempo_bpm"]
    return {
        "seed_id": f"{seed_prefix}_{uuid.uuid4().hex[:10]}",
        "bpm": float(tb["target"]),
        "lufs_profile": "streaming_minus14_lufs_v1",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Lens music gematria → symbolic safety → audio gate chain (v1).")
    ap.add_argument("--lens-json", type=Path, required=True, help="lens_music_gematria_v1 JSON path.")
    ap.add_argument("--symbolic-policy", choices=("hold", "clip"), default="hold")
    ap.add_argument("--wav", type=Path, default=None, help="16-bit mono WAV for mechanical gate.")
    ap.add_argument("--emit-placeholder-wav", type=Path, default=None, help="Write silence WAV here if --wav missing.")
    ap.add_argument("--field-policy", type=Path, default=ROOT / "policies/audio_copyright_field.json")
    ap.add_argument("--track", choices=("A", "B"), default="B")
    ap.add_argument(
        "--commercial-terms-tag",
        type=str,
        default="apache2_self_host_weights_v1",
        help="Provenance tag for copyright field gate (empty string = omit; often FAIL commercial check).",
    )
    ap.add_argument(
        "--strict-lufs",
        action="store_true",
        help="Measure LUFS (needs pyloudnorm); default waives for CI/no-deps smoke.",
    )
    ap.add_argument(
        "--strict-bpm-lens",
        action="store_true",
        help="Require BPM lens alignment; default waives (no detector in stub chain).",
    )
    ap.add_argument("--export-chain", type=Path, default=ROOT / "reports/lens_music_gate_chain_v1_latest.json")
    ap.add_argument("--export-audio-report", type=Path, default=ROOT / "reports/audio_gate_lens_music_chain_latest.json")
    ap.add_argument("--run-id", type=str, default="")
    args = ap.parse_args()

    lens_doc = _load_json(args.lens_json)

    try:
        _validate_lens_envelope(lens_doc)
        raw_outputs = _resolve_outputs(lens_doc)
    except Exception as e:
        print(f"error: invalid lens document: {e}", file=sys.stderr)
        return 2

    sym_decision, eff_outputs, sym_reasons, clip_notes = evaluate_symbolic_safety(
        raw_outputs,
        policy=args.symbolic_policy,
    )

    chain: dict[str, Any] = {
        "schema": CHAIN_SCHEMA,
        "version": CHAIN_VERSION,
        "symbolic_stage": {
            "decision": sym_decision,
            "policy": args.symbolic_policy,
            "reasons": sym_reasons,
            "clip_notes": clip_notes,
            "effective_outputs": eff_outputs,
        },
        "audio_gate": {"skipped": True, "reason": None},
    }
    evo = lens_doc.get("emotion_va_overlay_v1")
    if isinstance(evo, dict):
        chain["emotion_va_overlay_v1"] = evo

    if sym_decision == "HOLD":
        chain["audio_gate"] = {"skipped": True, "reason": "symbolic_hold"}
        chain["final_decision"] = "HOLD"
        args.export_chain.parent.mkdir(parents=True, exist_ok=True)
        args.export_chain.write_text(json.dumps(chain, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(json.dumps({"ok": False, "stage": "symbolic", "chain_report": str(args.export_chain)}, indent=2))
        return 2

    wav_path = args.wav
    if wav_path is None or not wav_path.is_file():
        emit = args.emit_placeholder_wav
        if emit is None:
            emit = ROOT / "reports/tmp_lens_music_chain_silence.wav"
        gen = ROOT / "scripts/audio/generate_placeholder_wav.py"
        r = subprocess.run(
            [sys.executable, str(gen), "--out", str(emit), "--seconds", "2", "--kind", "silence"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            print(r.stderr, file=sys.stderr)
            return 2
        wav_path = emit

    seed = build_seed_from_outputs(eff_outputs, seed_prefix="lmg")
    seed_path = args.export_audio_report.with_suffix(".seed.json")
    seed_path.parent.mkdir(parents=True, exist_ok=True)
    seed_path.write_text(json.dumps(seed, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    prov: dict[str, Any] = {
        "provider": "lens_music_gematria_gate_chain_v1",
        "model_id": "symbolic_stub_chain",
        "request_reference": str(args.lens_json.resolve()),
    }
    tag = (args.commercial_terms_tag or "").strip()
    if tag:
        prov["commercial_terms_tag"] = tag

    meta_path = wav_path.with_suffix(".meta.json")
    meta_path.write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    from scripts.audio.evaluate_audio_gate import build_report

    field_policy = _load_json(args.field_policy)
    run_id = args.run_id.strip() or uuid.uuid4().hex[:16]
    loop_join_policy = {
        "crossfade_ms": 12.0,
        "max_join_sample_jump": 0.02,
        "eval_window_samples": 2048,
    }

    report = build_report(
        wav_path=wav_path,
        field_policy=field_policy,
        seed=seed,
        provenance=prov,
        track=args.track,
        run_id=run_id,
        lufs_profile=str(seed.get("lufs_profile", "streaming_minus14_lufs_v1")),
        loop_join_policy=loop_join_policy,
        waive_lufs=not args.strict_lufs,
        waive_bpm_lens=not args.strict_bpm_lens,
    )

    args.export_audio_report.parent.mkdir(parents=True, exist_ok=True)
    args.export_audio_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    chain["audio_gate"] = {
        "skipped": False,
        "report_path": str(args.export_audio_report.as_posix()),
        "seed_path": str(seed_path.as_posix()),
        "decision": report["decision"],
        "wav_path": str(wav_path.as_posix()),
    }
    chain["final_decision"] = report["decision"]

    args.export_chain.parent.mkdir(parents=True, exist_ok=True)
    args.export_chain.write_text(json.dumps(chain, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    ok = report["decision"] == "PASS"
    print(
        json.dumps(
            {
                "ok": ok,
                "symbolic": sym_decision,
                "audio_gate": report["decision"],
                "chain_report": str(args.export_chain),
                "audio_report": str(args.export_audio_report),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
