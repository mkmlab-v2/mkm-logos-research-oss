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

    if seed and "bpm" in seed:
        if waive_bpm_lens:
            skipped.append("bpm_lens_waived_explicit_cli")
            metrics["lens_alignment_pass"] = True
        else:
            skipped.append("bpm_lens_alignment_requires_detector_v1")
            metrics["lens_alignment_pass"] = False
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
        "tool_versions": {"evaluate_audio_gate": "1.0.0"},
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
        help="PASS lens_alignment when seed has bpm but detector is not wired (explicit waiver).",
    )
    args = ap.parse_args()

    wav_path = _pick_wav(args.input_dir, args.wav)
    if wav_path is None:
        print("No WAV found; nothing to evaluate.")
        return 2

    field_policy = _load_json(args.field_policy)
    seed = _load_json(args.seed_json) if args.seed_json else None
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
        waive_lufs=args.waive_lufs,
        waive_bpm_lens=args.waive_bpm_lens,
    )

    args.export_report.parent.mkdir(parents=True, exist_ok=True)
    args.export_report.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": report["decision"], "report": str(args.export_report)}, indent=2))
    return 0 if report["decision"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
