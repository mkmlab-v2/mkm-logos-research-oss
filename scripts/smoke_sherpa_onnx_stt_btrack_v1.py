#!/usr/bin/env py
"""B-track [HYPO] — local Sherpa-ONNX STT smoke + stt_routing_audit_log_v1 append."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tarfile
import time
import urllib.request
import wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WAV = ROOT / "reports/audio/supertonic_btrack_smoke_v1.wav"
OUT = ROOT / "reports/sherpa_onnx_stt_btrack_smoke_v1_latest.json"
AUDIT_JSONL = ROOT / "reports/stt_routing_audit_log_v1.jsonl"
VENV_DIR = ROOT / ".venv-btrack-sherpa-onnx"
VENV_PY = VENV_DIR / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
WORKER_ENV = "MKM_SHERPA_BTRACK_WORKER"
MODEL_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
)
MODEL_ROOT = (
    ROOT
    / "reports/constitution/btrack_pilot/sherpa_onnx_models"
    / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17"
)
SUPER_TTS_REF = ROOT / "reports/supertonic_tts_btrack_smoke_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _wav_duration_ms(wav_path: Path) -> int:
    with wave.open(str(wav_path), "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        if rate <= 0:
            return 0
        return int(round(1000.0 * frames / rate))


def _norm(text: str) -> str:
    return re.sub(r"[^\w\uac00-\ud7a3]+", "", text.strip().lower())


def _normalize_korean_numbers(text: str) -> str:
    out = text
    replacements = {
        "0": "영",
        "1": "일",
        "2": "이",
        "3": "삼",
        "4": "사",
        "5": "오",
        "6": "육",
        "7": "칠",
        "8": "팔",
        "9": "구",
    }
    for src, dst in replacements.items():
        out = out.replace(src, dst)
    out = out.replace("하나", "일").replace("둘", "이").replace("셋", "삼")
    out = out.replace("넷", "사").replace("다섯", "오").replace("여섯", "육")
    out = out.replace("일일", "하루")
    return out


def _levenshtein(a: str, b: str) -> int:
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, start=1):
        curr = [i]
        for j, cb in enumerate(b, start=1):
            cost = 0 if ca == cb else 1
            curr.append(min(curr[-1] + 1, prev[j] + 1, prev[j - 1] + cost))
        prev = curr
    return prev[-1]


def _load_default_reference_text() -> str:
    if not SUPER_TTS_REF.is_file():
        return ""
    try:
        doc = json.loads(SUPER_TTS_REF.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return ""
    return str(doc.get("sample_text") or "").strip()


def _attach_quality(report: dict[str, object], *, transcript: str, reference_text: str) -> None:
    if not reference_text.strip():
        return
    ref = _norm(reference_text)
    hyp = _norm(transcript)
    dist = _levenshtein(ref, hyp)
    denom = max(1, len(ref))
    cer = dist / denom

    ref_num = _norm(_normalize_korean_numbers(reference_text))
    hyp_num = _norm(_normalize_korean_numbers(transcript))
    dist_num = _levenshtein(ref_num, hyp_num)
    denom_num = max(1, len(ref_num))
    cer_num = dist_num / denom_num

    report.update(
        {
            "reference_text": reference_text,
            "reference_norm": ref,
            "transcript_norm": hyp,
            "char_error_rate": round(cer, 6),
            "char_accuracy": round(max(0.0, 1.0 - cer), 6),
            "reference_norm_number_aware": ref_num,
            "transcript_norm_number_aware": hyp_num,
            "char_error_rate_number_aware": round(cer_num, 6),
            "char_accuracy_number_aware": round(max(0.0, 1.0 - cer_num), 6),
        }
    )


def _append_audit_row(*, audio_ms: int, session_id: str, audit_out: Path) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts/append_stt_routing_audit_log_v1.py"),
        "--out",
        str(audit_out),
        "--route",
        "local",
        "--audio-ms",
        str(audio_ms),
        "--session-id",
        session_id,
        "--pii-redaction",
        "redacted_full",
        "--hypothesis-tag",
        "[HYPO]",
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "append_stt_routing_audit_log failed")


def _ensure_sense_voice_model() -> tuple[Path, Path]:
    model_onnx = MODEL_ROOT / "model.onnx"
    tokens = MODEL_ROOT / "tokens.txt"
    if model_onnx.is_file() and tokens.is_file():
        return model_onnx, tokens

    MODEL_ROOT.parent.mkdir(parents=True, exist_ok=True)
    archive = MODEL_ROOT.parent / "sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17.tar.bz2"
    if not archive.is_file():
        urllib.request.urlretrieve(MODEL_URL, archive)
    if MODEL_ROOT.is_dir():
        for child in MODEL_ROOT.iterdir():
            if child.is_dir():
                import shutil

                shutil.rmtree(child, ignore_errors=True)
    MODEL_ROOT.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive, "r:bz2") as tf:
        tf.extractall(MODEL_ROOT.parent)
    model_onnx = MODEL_ROOT / "model.onnx"
    tokens = MODEL_ROOT / "tokens.txt"
    if not model_onnx.is_file() or not tokens.is_file():
        raise FileNotFoundError(f"sense-voice model missing under {MODEL_ROOT}")
    return model_onnx, tokens


def _load_wav_float32_16k(wav_path: Path) -> tuple[list[float], int]:
    import numpy as np

    try:
        import soundfile as sf  # type: ignore
    except ImportError as exc:
        raise ImportError("soundfile required in sherpa venv") from exc

    samples, sample_rate = sf.read(str(wav_path), dtype="float32", always_2d=False)
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    if sample_rate != 16000:
        duration = len(samples) / float(sample_rate)
        n_out = max(1, int(round(duration * 16000)))
        x_old = np.linspace(0.0, duration, num=len(samples), endpoint=False)
        x_new = np.linspace(0.0, duration, num=n_out, endpoint=False)
        samples = np.interp(x_new, x_old, samples).astype(np.float32)
        sample_rate = 16000
    return samples.tolist(), sample_rate


def _transcribe_local(wav_path: Path) -> dict[str, object]:
    import sherpa_onnx  # type: ignore

    model_onnx, tokens = _ensure_sense_voice_model()
    waveform, sample_rate = _load_wav_float32_16k(wav_path)
    t0 = time.perf_counter()
    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(model_onnx),
        tokens=str(tokens),
        num_threads=1,
        use_itn=False,
        debug=False,
    )
    stream = recognizer.create_stream()
    stream.accept_waveform(sample_rate, waveform)
    recognizer.decode_stream(stream)
    elapsed_ms = int(round((time.perf_counter() - t0) * 1000))
    text = (stream.result.text or "").strip()
    return {
        "transcript": text,
        "transcript_chars": len(text),
        "decode_ms": elapsed_ms,
        "model_dir": _rel(model_onnx.parent),
    }


def _run_worker_subprocess(python_exe: Path, wav_path: Path, audit_out: Path) -> tuple[int, dict | None, str]:
    env = os.environ.copy()
    env[WORKER_ENV] = "1"
    proc = subprocess.run(
        [
            str(python_exe),
            str(Path(__file__).resolve()),
            "--wav",
            str(wav_path),
            "--audit-out",
            str(audit_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    raw = (proc.stdout or proc.stderr).strip()
    if not raw:
        return proc.returncode, None, "empty_worker_output"
    try:
        payload = json.loads(raw.splitlines()[-1])
    except json.JSONDecodeError:
        return proc.returncode, None, raw[-500:]
    return proc.returncode, payload, ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--wav", type=Path, default=DEFAULT_WAV)
    ap.add_argument("--audit-out", type=Path, default=AUDIT_JSONL)
    ap.add_argument(
        "--fixture-only",
        action="store_true",
        help="Append route=local audit row from wav duration only (no Sherpa)",
    )
    ap.add_argument("--session-id", default="sherpa_btrack_smoke_v1")
    ap.add_argument(
        "--reference-text",
        default="",
        help="Optional reference text for inline quality metrics (default: supertonic sample_text)",
    )
    args = ap.parse_args()

    report: dict[str, object] = {
        "schema": "sherpa_onnx_stt_btrack_smoke_v1",
        "lane": "b_track_hypo",
        "generated_at_utc": _utc_now(),
        "reproduce": "py scripts/smoke_sherpa_onnx_stt_btrack_v1.py",
        "reproduce_venv": (
            "powershell -File scripts/Invoke-SherpaOnnxSttBtrackSmoke_v1.ps1 -BootstrapVenv"
        ),
        "wav_path": _rel(args.wav),
        "audit_jsonl": _rel(args.audit_out),
    }

    if not args.wav.is_file():
        report.update({"status": "fail", "error": "wav_missing", "detail": str(args.wav)})
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1

    audio_ms = _wav_duration_ms(args.wav)
    reference_text = (args.reference_text or "").strip() or _load_default_reference_text()

    if args.fixture_only:
        _append_audit_row(audio_ms=audio_ms, session_id=args.session_id, audit_out=args.audit_out)
        report.update(
            {
                "status": "ok_fixture_audit",
                "audio_duration_ms": audio_ms,
                "session_id": args.session_id,
                "route": "local",
                "runtime": "fixture_audit_only",
            }
        )
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    if os.environ.get(WORKER_ENV) == "1":
        try:
            tx = _transcribe_local(args.wav)
            _append_audit_row(audio_ms=audio_ms, session_id=args.session_id, audit_out=args.audit_out)
            report.update(
                {
                    "status": "ok",
                    "audio_duration_ms": audio_ms,
                    "session_id": args.session_id,
                    "route": "local",
                    "runtime": "worker",
                    **tx,
                }
            )
            _attach_quality(report, transcript=str(report.get("transcript") or ""), reference_text=reference_text)
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            return 0
        except Exception as exc:  # noqa: BLE001
            report.update({"status": "fail", "error": str(exc), "runtime": "worker"})
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
            return 1

    if VENV_PY.is_file():
        code, payload, detail = _run_worker_subprocess(VENV_PY, args.wav, args.audit_out)
        if code == 0 and payload and payload.get("status") == "ok":
            report.update(payload)
            report["runtime"] = "venv_subprocess"
            report["venv_python"] = _rel(VENV_PY)
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False))
            return 0
        if payload:
            report.update(payload)
            report["worker_detail"] = detail
            OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
            return 1 if payload.get("status") == "fail" else 0

    try:
        import sherpa_onnx  # type: ignore  # noqa: F401
    except Exception as exc:  # noqa: BLE001
        report.update(
            {
                "status": "skip",
                "reason": "sherpa_onnx_unavailable",
                "detail": str(exc)[:500],
                "hint": (
                    "powershell -File scripts/Invoke-SherpaOnnxSttBtrackSmoke_v1.ps1 -BootstrapVenv "
                    "or --fixture-only"
                ),
                "venv_expected": _rel(VENV_DIR),
            }
        )
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0

    try:
        tx = _transcribe_local(args.wav)
        _append_audit_row(audio_ms=audio_ms, session_id=args.session_id, audit_out=args.audit_out)
        report.update(
            {
                "status": "ok",
                "audio_duration_ms": audio_ms,
                "session_id": args.session_id,
                "route": "local",
                "runtime": "in_process",
                **tx,
            }
        )
        _attach_quality(report, transcript=str(report.get("transcript") or ""), reference_text=reference_text)
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except Exception as exc:  # noqa: BLE001
        report.update({"status": "fail", "error": str(exc)})
        OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
