"""
MKM AI audio pipeline — batch generation harness (Formula layer).

``--emit external`` runs ``MKM_AUDIO_EXTERNAL_SCRIPT`` (path relative to repo root). Examples:
``gemini_placeholder_external_generator_v1.py`` (Gemini expand + WAV hook),
``tone_external_generator_v1.py`` (offline sine bed),
``expand_tone_external_generator_v1.py`` (expand + tone),
``ffmpeg_bed_external_generator_v1.py`` (lavfi colored noise; ``ffmpeg`` on PATH).

PowerShell entrypoints: ``scripts/Run-AudioBgmGeminiExternalChain_v1.ps1``,
``scripts/Run-AudioBgmEconomyChain_v1.ps1``. Strict LUFS deps probe:
``scripts/audio/check_audio_gate_optional_deps_v1.py``.

Default output/log paths align with local Fact-Lock (reports/ is gitignored noise).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _default_provenance(run_id: str, seed_id: str) -> dict:
    return {
        "provider": "placeholder_local",
        "model_id": "generate_placeholder_wav",
        "model_version": "1.0.0",
        "commercial_terms_tag": "apache2_self_host_weights_v1",
        "request_reference": run_id,
        "seed_id": seed_id,
    }


def _write_silence_wav(path: Path, seconds: float, sample_rate: int = 48000) -> None:
    """Mono 16-bit PCM silence (stdlib only)."""
    import wave

    n = max(1, int(seconds * sample_rate))
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(b"\x00\x00" * n)


def main() -> int:
    p = argparse.ArgumentParser(description="BGM batch generation placeholder + JSONL log line.")
    p.add_argument("--seed-json", type=Path, required=True, help="Path to seed JSON (see data/audio/seeds/*.example.json).")
    p.add_argument("--count", type=int, default=1, help="Requested renders (log only; wire API separately).")
    p.add_argument("--output-dir", type=Path, default=Path("workspace/audio_raw"))
    p.add_argument(
        "--emit",
        choices=("none", "placeholder", "external"),
        default="none",
        help="none=log only; placeholder=silence WAV; external=MKM_AUDIO_EXTERNAL_SCRIPT subprocess (see module docstring).",
    )
    p.add_argument(
        "--write-placeholder-wav",
        action="store_true",
        help="Same as --emit placeholder.",
    )
    p.add_argument(
        "--placeholder-seconds",
        type=float,
        default=2.0,
        help="Duration seconds per WAV for placeholder or external stub backends.",
    )
    p.add_argument(
        "--provenance-json",
        type=Path,
        default=None,
        help="Optional provenance template JSON (merged over defaults).",
    )
    p.add_argument(
        "--log-jsonl",
        type=Path,
        default=Path("reports/audio/generation_batches.jsonl"),
        help="Append-only generation audit log (under reports/ by default).",
    )
    p.add_argument("--run-id", type=str, default="", help="Optional run id (default: uuid).")
    p.add_argument(
        "--run-gate",
        action="store_true",
        help="After WAVs exist, run scripts/audio/evaluate_audio_gate.py per file (needs matching .meta.json).",
    )
    p.add_argument(
        "--gate-export-dir",
        type=Path,
        default=Path("reports/audio"),
        help="Directory for per-index audio_gate_<run_id>_NNN.json reports.",
    )
    p.add_argument("--gate-waive-lufs", action="store_true", help="Forwarded to evaluate_audio_gate.")
    p.add_argument("--gate-waive-bpm-lens", action="store_true", help="Forwarded to evaluate_audio_gate.")
    p.add_argument("--gate-track", choices=("A", "B"), default="A")
    p.add_argument(
        "--gate-relaxed",
        action="store_true",
        help="Do not fail the batch process when a gate report is FAIL (still writes reports).",
    )
    p.add_argument(
        "--gate-skip-latest-copy",
        action="store_true",
        help="Do not mirror first WAV gate report to reports/audio_gate_latest.json.",
    )
    args = p.parse_args()

    emit_mode = "placeholder" if args.write_placeholder_wav else args.emit

    seed = _load_json(args.seed_json)
    run_id = args.run_id.strip() or uuid.uuid4().hex[:16]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.log_jsonl.parent.mkdir(parents=True, exist_ok=True)

    seed_canonical = json.dumps(seed, sort_keys=True, ensure_ascii=False)
    seed_hash = hashlib.sha256(seed_canonical.encode("utf-8")).hexdigest()
    seed_id = str(seed.get("seed_id", "unknown"))

    written_wavs: list[str] = []
    if emit_mode == "placeholder":
        prov = _default_provenance(run_id, seed_id)
        if args.provenance_json and args.provenance_json.is_file():
            extra = _load_json(args.provenance_json)
            prov.update(extra)
        sr = 48000
        for i in range(args.count):
            stem = f"bgm_{run_id}_{i:03d}"
            wav_path = args.output_dir / f"{stem}.wav"
            meta_path = args.output_dir / f"{stem}.meta.json"
            _write_silence_wav(wav_path, args.placeholder_seconds, sr)
            meta_path.write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written_wavs.append(str(wav_path.as_posix()))
    elif emit_mode == "external":
        script_raw = (os.environ.get("MKM_AUDIO_EXTERNAL_SCRIPT") or "").strip()
        if not script_raw:
            print(json.dumps({"ok": False, "error": "MKM_AUDIO_EXTERNAL_SCRIPT environment variable is required for --emit external"}, indent=2))
            return 4
        script_path = Path(script_raw)
        if not script_path.is_absolute():
            script_path = (_REPO_ROOT / script_path).resolve()
        if not script_path.is_file():
            print(json.dumps({"ok": False, "error": f"external script not found: {script_path}"}, indent=2))
            return 4
        timeout_s = int((os.environ.get("MKM_AUDIO_EXTERNAL_TIMEOUT_SEC") or "600").strip() or "600")
        seed_abs = args.seed_json.resolve()
        for i in range(args.count):
            stem = f"bgm_{run_id}_{i:03d}"
            wav_path = args.output_dir / f"{stem}.wav"
            meta_path = args.output_dir / f"{stem}.meta.json"
            cmd = [
                sys.executable,
                str(script_path),
                "--seed-json",
                str(seed_abs),
                "--out-wav",
                str(wav_path.resolve()),
                "--index",
                str(i),
                "--run-id",
                run_id,
                "--seconds",
                str(args.placeholder_seconds),
            ]
            try:
                subprocess.run(cmd, check=True, timeout=timeout_s, cwd=str(_REPO_ROOT))
            except subprocess.CalledProcessError as e:
                print(json.dumps({"ok": False, "error": "external_generator_failed", "returncode": e.returncode}, indent=2))
                return 5
            except subprocess.TimeoutExpired:
                print(json.dumps({"ok": False, "error": "external_generator_timeout", "timeout_sec": timeout_s}, indent=2))
                return 6
            prov = _default_provenance(run_id, seed_id)
            if args.provenance_json and args.provenance_json.is_file():
                extra = _load_json(args.provenance_json)
                prov.update(extra)
            expand_sidecar = wav_path.with_suffix(".expand.json")
            if expand_sidecar.is_file():
                try:
                    exp = _load_json(expand_sidecar)
                    prov["gemini_seed_expand"] = {
                        "path": str(expand_sidecar.as_posix()),
                        "billing_surface": exp.get("billing_surface"),
                        "model": exp.get("model"),
                    }
                except Exception:
                    pass
            meta_path.write_text(json.dumps(prov, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            written_wavs.append(str(wav_path.as_posix()))

    row = {
        "schema": "audio_generation_batch_log_v1",
        "run_id": run_id,
        "ts_utc": _utc_now_iso(),
        "seed_path": str(args.seed_json.as_posix()),
        "seed_hash": f"sha256:{seed_hash}",
        "requested_count": args.count,
        "output_dir": str(args.output_dir.as_posix()),
        "emit_mode": emit_mode,
        "status": (
            "placeholder_wav"
            if emit_mode == "placeholder"
            else "external_wav"
            if emit_mode == "external"
            else "logged_stub"
        ),
        "written_wavs": written_wavs,
        "note": "Wire model/API under scripts/audio; keep logs append-only.",
    }

    gate_summary_path: str | None = None
    gate_failed = False
    if args.run_gate and written_wavs:
        args.gate_export_dir.mkdir(parents=True, exist_ok=True)
        gate_rows: list[dict] = []
        seed_abs = args.seed_json.resolve()
        for idx, wav_str in enumerate(written_wavs):
            wav_path = Path(wav_str)
            meta_path = wav_path.with_suffix(".meta.json")
            export_path = args.gate_export_dir / f"audio_gate_{run_id}_{idx:03d}.json"
            cmd = [
                sys.executable,
                str(_REPO_ROOT / "scripts/audio/evaluate_audio_gate.py"),
                "--wav",
                str(wav_path.resolve()),
                "--seed-json",
                str(seed_abs),
                "--run-id",
                run_id,
                "--track",
                args.gate_track,
                "--export-report",
                str(export_path.resolve()),
            ]
            if meta_path.is_file():
                cmd.extend(["--provenance-json", str(meta_path.resolve())])
            if args.gate_waive_lufs:
                cmd.append("--waive-lufs")
            if args.gate_waive_bpm_lens:
                cmd.append("--waive-bpm-lens")
            gr = subprocess.run(cmd, cwd=str(_REPO_ROOT))
            if gr.returncode != 0:
                gate_failed = True
            decision = "UNKNOWN"
            if export_path.is_file():
                try:
                    decision = str(_load_json(export_path).get("decision", "UNKNOWN"))
                except Exception:
                    pass
            gate_rows.append(
                {
                    "wav": wav_str,
                    "export_report": str(export_path.as_posix()),
                    "evaluate_exit_code": gr.returncode,
                    "decision": decision,
                }
            )
        gate_summary_path_str = str((args.gate_export_dir / f"_gates_summary_{run_id}.json").resolve())
        gate_summary_path = gate_summary_path_str
        Path(gate_summary_path_str).write_text(
            json.dumps(
                {"schema": "audio_batch_gate_summary_v1", "run_id": run_id, "gates": gate_rows},
                indent=2,
                ensure_ascii=False,
            )
            + "\n",
            encoding="utf-8",
        )
        if not args.gate_skip_latest_copy and gate_rows:
            first_rep = Path(gate_rows[0]["export_report"])
            if first_rep.is_file():
                latest_gate = _REPO_ROOT / "reports/audio_gate_latest.json"
                latest_gate.parent.mkdir(parents=True, exist_ok=True)
                latest_gate.write_text(first_rep.read_text(encoding="utf-8"), encoding="utf-8")

    if gate_summary_path:
        row["gate_summary_path"] = gate_summary_path
        row["gate_all_pass"] = not gate_failed

    summary_path = args.output_dir / f"_batch_{run_id}.json"
    with args.log_jsonl.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    summary_path.write_text(json.dumps(row, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    out = {"ok": True, "run_id": run_id, "log": str(args.log_jsonl), "summary": str(summary_path)}
    if gate_summary_path:
        out["gate_summary"] = gate_summary_path
    print(json.dumps(out, indent=2))

    if args.run_gate and written_wavs and gate_failed and not args.gate_relaxed:
        return 7
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
