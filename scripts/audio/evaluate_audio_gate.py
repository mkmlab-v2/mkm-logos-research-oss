"""
MKM AI audio pipeline — mechanical gate evaluation (Label + Field layers).

Measures DoD-style metrics where possible using stdlib WAV IO; optional pyloudnorm
for integrated LUFS when installed.
"""

from __future__ import annotations

import argparse
import json
import math
import struct
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts.audio.detect_bpm_v1 import bpm_delta_pct, measure_bpm_v1
except ModuleNotFoundError:
    from detect_bpm_v1 import bpm_delta_pct, measure_bpm_v1


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _policy_allows_commercial(field_policy: dict[str, Any], terms_tag: str | None) -> bool:
    allow = field_policy.get("commercial_model_allowlist") or []
    ids = {entry.get("id") for entry in allow if isinstance(entry, dict)}
    return bool(terms_tag) and terms_tag in ids


def _read_wav_normalized(path: Path) -> tuple[list[float], int, int]:
    """Return mono float samples in [-1,1], sample_rate, sample_width."""
    with wave.open(str(path), "rb") as wf:
        nch = wf.getnchannels()
        sw = wf.getsampwidth()
        sr = wf.getframerate()
        nframes = wf.getnframes()
        raw = wf.readframes(nframes)

    if sw != 2:
        raise ValueError(f"Only 16-bit PCM WAV supported for gate v1; got width={sw}")

    nch = max(1, nch)
    nsamples = len(raw) // (sw * nch)
    out: list[float] = []
    for i in range(nsamples):
        frame = raw[i * sw * nch : (i + 1) * sw * nch]
        acc = 0.0
        for ch in range(nch):
            sample = struct.unpack_from("<h", frame, ch * sw)[0]
            acc += sample / 32768.0
        out.append(acc / nch)
    return out, sr, sw


def _measure_loop_seam(samples: list[float], max_jump: float, window: int) -> tuple[bool, float]:
    if len(samples) < window * 2:
        return False, float("nan")
    jump = abs(samples[-1] - samples[0])
    head = samples[:window]
    tail = samples[-window:]
    rms_head = math.sqrt(sum(x * x for x in head) / len(head))
    rms_tail = math.sqrt(sum(x * x for x in tail) / len(tail))
    rel = abs(rms_tail - rms_head) / max(rms_head + rms_tail, 1e-9)
    ok = jump <= max_jump and rel <= 0.25
    return ok, jump


def _measure_lufs(path: Path) -> tuple[bool, float | None, bool]:
    """Returns (match, integrated_lufs_or_none, measured_flag)."""
    try:
        import numpy as np  # type: ignore
        import pyloudnorm as pyln  # type: ignore
    except ImportError:
        return False, None, False

    data, rate, _ = _read_wav_normalized(path)
    meter = pyln.Meter(rate)
    arr = np.array(data, dtype=np.float64).reshape((-1, 1))
    loudness = meter.integrated_loudness(arr)
    target = -14.0
    ok = abs(float(loudness) - target) <= 1.0
    return ok, float(loudness), True


def _pick_wav(input_dir: Path, explicit: Path | None) -> Path | None:
    if explicit is not None:
        return explicit if explicit.is_file() else None
    wavs = sorted(input_dir.glob("*.wav"))
    return wavs[0] if wavs else None


def _resolve_bpm_target(seed: dict[str, Any] | None, conditioning: dict[str, Any] | None) -> tuple[float, str | None]:
    """Prefer conditioning tempo_bpm_target over seed bpm when present."""
    if conditioning:
        cond = conditioning.get("conditioning") or {}
        tempo = cond.get("tempo_bpm_target")
        if isinstance(tempo, (int, float)) and float(tempo) > 0:
            return float(tempo), "conditioning"
    if seed and isinstance(seed.get("bpm"), (int, float)) and float(seed["bpm"]) > 0:
        return float(seed["bpm"]), "seed"
    return 0.0, None


def _evaluate_bpm_lens(
    samples: list[float],
    sample_rate: int,
    seed: dict[str, Any],
    track: str,
    *,
    target_bpm: float | None = None,
    target_bpm_source: str | None = None,
    max_delta_pct: float = 12.0,
    min_confidence: float = 0.25,
) -> tuple[bool, list[str], dict[str, Any]]:
    """Returns (lens_pass, skipped_reasons, metric_fields)."""
    skipped: list[str] = []
    fields: dict[str, Any] = {}
    if target_bpm is None:
        target_bpm, target_bpm_source = _resolve_bpm_target(seed, None)
    if target_bpm <= 0:
        return True, skipped, fields
    if target_bpm_source:
        fields["bpm_target"] = target_bpm
        fields["bpm_target_source"] = target_bpm_source

    if isinstance(seed.get("bpm_max_delta_pct"), (int, float)):
        max_delta_pct = float(seed["bpm_max_delta_pct"])

    observed, confidence = measure_bpm_v1(samples, sample_rate)
    if observed is None or confidence < min_confidence:
        if track == "B":
            skipped.append("bpm_detector_low_confidence_b_track")
            return True, skipped, fields
        skipped.append("bpm_detector_low_confidence")
        return False, skipped, fields

    delta = bpm_delta_pct(observed, target_bpm)
    fields["bpm_observed"] = observed
    fields["bpm_delta_pct"] = delta
    harmonic_delta = bpm_delta_pct(observed * 2.0, target_bpm)
    half_delta = bpm_delta_pct(observed / 2.0, target_bpm) if observed >= 2.0 else 999.0
    best_delta = min(delta, harmonic_delta, half_delta)
    fields["bpm_delta_pct"] = best_delta
    return best_delta <= max_delta_pct, skipped, fields


def build_report(
    *,
    wav_path: Path,
    field_policy: dict[str, Any],
    seed: dict[str, Any] | None,
    provenance: dict[str, Any],
    track: str,
    run_id: str,
    lufs_profile: str,
    loop_join_policy: dict[str, Any],
    conditioning: dict[str, Any] | None = None,
    waive_lufs: bool = False,
    waive_bpm_lens: bool = False,
) -> dict[str, Any]:
    skipped: list[str] = []
    metrics: dict[str, Any] = {
        "loop_seamlessness_pass": False,
        "lufs_target_match": False,
        "commercial_license_verified": False,
        "lens_alignment_pass": False,
    }

    samples, _sr, _sw = _read_wav_normalized(wav_path)
    ok_loop, jump = _measure_loop_seam(
        samples,
        float(loop_join_policy["max_join_sample_jump"]),
        int(loop_join_policy["eval_window_samples"]),
    )
    metrics["loop_seamlessness_pass"] = ok_loop

    lufs_ok, lufs_val, lufs_measured = _measure_lufs(wav_path)
    if waive_lufs:
        skipped.append("lufs_waived_explicit_cli")
        metrics["lufs_target_match"] = True
        if lufs_measured:
            metrics["lufs_integrated"] = lufs_val
    elif lufs_measured:
        metrics["lufs_target_match"] = lufs_ok
        metrics["lufs_integrated"] = lufs_val
    else:
        skipped.append("lufs_skipped_missing_pyloudnorm_or_numpy")
        metrics["lufs_target_match"] = False

    terms_tag = provenance.get("commercial_terms_tag")
    metrics["commercial_license_verified"] = _policy_allows_commercial(field_policy, terms_tag)
    if track == "A" and not terms_tag:
        skipped.append("commercial_terms_tag_required_for_track_a")

    bpm_target, bpm_target_source = _resolve_bpm_target(seed, conditioning)
    if bpm_target > 0:
        if waive_bpm_lens:
            skipped.append("bpm_lens_waived_explicit_cli")
            metrics["lens_alignment_pass"] = True
        else:
            lens_ok, bpm_skipped, bpm_fields = _evaluate_bpm_lens(
                samples,
                _sr,
                seed or {},
                track,
                target_bpm=bpm_target,
                target_bpm_source=bpm_target_source,
            )
            skipped.extend(bpm_skipped)
            metrics.update(bpm_fields)
            metrics["lens_alignment_pass"] = lens_ok
    else:
        metrics["lens_alignment_pass"] = True

    if skipped:
        metrics["skipped_checks"] = skipped

    failure_reasons: list[str] = []
    if not metrics["loop_seamlessness_pass"]:
        failure_reasons.append(f"loop_seam_jump={jump:.5f}")
    if not metrics["lufs_target_match"]:
        failure_reasons.append("lufs_target_mismatch_or_unmeasured")
    if not metrics["commercial_license_verified"]:
        failure_reasons.append("commercial_license_not_verified")
    if not metrics["lens_alignment_pass"]:
        failure_reasons.append("lens_alignment_failed")

    decision = "PASS" if not failure_reasons else "FAIL"

    prov_out: dict[str, Any] = {
        "provider": str(provenance.get("provider", "unknown")),
        "model_id": str(provenance.get("model_id", "unknown")),
        "terms_checked_at_utc": _utc_now_iso(),
    }
    if provenance.get("model_version") is not None:
        prov_out["model_version"] = str(provenance["model_version"])
    if provenance.get("commercial_terms_tag") is not None:
        prov_out["commercial_terms_tag"] = str(provenance["commercial_terms_tag"])
    if provenance.get("request_reference") is not None:
        prov_out["request_reference"] = str(provenance["request_reference"])

    out: dict[str, Any] = {
        "schema": "audio_bgm_gate_report_v1",
        "version": "1.0.0",
        "run_id": run_id,
        "generated_at_utc": _utc_now_iso(),
        "track": track,
        "seed_id": str(seed.get("seed_id", "unknown")) if seed else "unknown",
        "lufs_profile": lufs_profile,
        "loop_join_policy": loop_join_policy,
        "metrics": metrics,
        "provenance": prov_out,
        "tool_versions": {"evaluate_audio_gate": "1.0.0", "detect_bpm_v1": "1.0.0"},
        "artifacts": {"wav_path": str(wav_path.as_posix())},
        "decision": decision,
    }
    if failure_reasons:
        out["failure_reasons"] = failure_reasons
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Evaluate BGM WAV against mechanical gate (v1).")
    ap.add_argument("--input-dir", type=Path, default=Path("workspace/audio_raw"))
    ap.add_argument("--wav", type=Path, default=None, help="Single WAV (overrides input-dir pick).")
    ap.add_argument("--field-policy", type=Path, default=Path("policies/audio_copyright_field.json"))
    ap.add_argument("--seed-json", type=Path, default=None)
    ap.add_argument(
        "--conditioning-json",
        type=Path,
        default=None,
        help="Optional sasang_music_conditioning_v1; tempo_bpm_target overrides seed bpm for lens check.",
    )
    ap.add_argument("--provenance-json", type=Path, default=None, help="Sidecar provenance.json.")
    ap.add_argument("--track", choices=("A", "B"), default="A")
    ap.add_argument("--run-id", type=str, default="")
    ap.add_argument("--export-report", type=Path, default=Path("reports/audio_gate_latest.json"))
    ap.add_argument(
        "--waive-lufs",
        action="store_true",
        help="PASS LUFS metric explicitly (audit: optional lufs_integrated when pyloudnorm runs); overrides measured mismatch.",
    )
    ap.add_argument(
        "--waive-bpm-lens",
        action="store_true",
        help="PASS lens_alignment explicitly (audit override; detector v1 is default when omitted).",
    )
    args = ap.parse_args()

    wav_path = _pick_wav(args.input_dir, args.wav)
    if wav_path is None:
        print("No WAV found; nothing to evaluate.")
        return 2

    field_policy = _load_json(args.field_policy)
    seed = _load_json(args.seed_json) if args.seed_json else None
    conditioning = _load_json(args.conditioning_json) if args.conditioning_json else None
    prov_path = args.provenance_json
    if prov_path is None:
        candidate = wav_path.with_suffix(".meta.json")
        if candidate.is_file():
            prov_path = candidate
    provenance = _load_json(prov_path) if prov_path and prov_path.is_file() else {}

    lufs_profile = str(seed.get("lufs_profile", "streaming_minus14_lufs_v1")) if seed else "streaming_minus14_lufs_v1"
    loop_join_policy = {
        "crossfade_ms": 12.0,
        "max_join_sample_jump": 0.02,
        "eval_window_samples": 2048,
    }
    run_id = args.run_id.strip() or uuid.uuid4().hex[:16]

    report = build_report(
        wav_path=wav_path,
        field_policy=field_policy,
        seed=seed,
        provenance=provenance,
        track=args.track,
        run_id=run_id,
        lufs_profile=lufs_profile,
        loop_join_policy=loop_join_policy,
        conditioning=conditioning,
        waive_lufs=args.waive_lufs,
        waive_bpm_lens=args.waive_bpm_lens,
    )

    args.export_report.parent.mkdir(parents=True, exist_ok=True)
    args.export_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": report["decision"], "report": str(args.export_report)}, indent=2))
    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
