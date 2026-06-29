#!/usr/bin/env py
"""B-track: Korean-only Supertonic->Sherpa STT benchmark (small phrase set)."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports" / "sherpa_onnx_stt_ko_phrase_benchmark_v1_latest.json"
AUDIO_DIR = ROOT / "reports" / "audio" / "sherpa_ko_bench_v1"
SMOKE_SCRIPT = ROOT / "scripts" / "smoke_sherpa_onnx_stt_btrack_v1.py"

PHRASES = [
    "오늘은 문서 자동화 품질 점검을 진행합니다.",
    "이 보고서는 연구 전용 경로에서만 사용합니다.",
    "개인정보는 로컬에서 마스킹 처리합니다.",
    "회의록 요약은 내부 검토 후에만 배포합니다.",
    "샘플 데이터는 비식별 처리 규칙을 준수합니다.",
    "이 모델은 실시간 상담 보조 용도로만 사용합니다.",
    "지표 이상 징후가 보이면 즉시 원인을 확인합니다.",
    "일일 리포트는 오전 아홉 시 전에 생성합니다.",
    "고유명사 인식률을 높이기 위해 사전을 보강합니다.",
    "보안 정책 위반 요청은 자동으로 차단합니다.",
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _norm(text: str) -> str:
    t = text.strip().lower()
    return re.sub(r"[^\w\uac00-\ud7a3]+", "", t)


def _normalize_korean_numbers(text: str) -> str:
    # Small, deterministic normalization for benchmark-only comparison.
    # Keeps semantic intent for common STT confusions (digit <-> Korean numerals).
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


def _synthesize(text: str, out_wav: Path) -> None:
    from supertonic import TTS  # type: ignore

    tts = TTS(auto_download=True)
    voice_name = (tts.voice_style_names or ["M1"])[0]
    style = tts.get_voice_style(voice_name)
    wav, _aux = tts.synthesize(text, voice_style=style, lang="ko")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    tts.save_audio(wav, str(out_wav))


def _run_sherpa(wav_path: Path, session_id: str) -> dict:
    cmd = [
        sys.executable,
        str(SMOKE_SCRIPT),
        "--wav",
        str(wav_path),
        "--session-id",
        session_id,
    ]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    raw = (proc.stdout or proc.stderr).strip()
    if proc.returncode != 0:
        raise RuntimeError(raw[-500:])
    return json.loads(raw.splitlines()[-1])


def main() -> int:
    rows: list[dict] = []
    failures: list[str] = []

    for idx, phrase in enumerate(PHRASES, start=1):
        wav_path = AUDIO_DIR / f"ko_phrase_{idx}.wav"
        session_id = f"sherpa_ko_bench_v1_{idx}"
        try:
            _synthesize(phrase, wav_path)
            hyp_doc = _run_sherpa(wav_path, session_id)
            hyp = str(hyp_doc.get("transcript") or "")
            ref_n = _norm(phrase)
            hyp_n = _norm(hyp)
            dist = _levenshtein(ref_n, hyp_n)
            denom = max(1, len(ref_n))
            cer = dist / denom
            ref_num = _norm(_normalize_korean_numbers(phrase))
            hyp_num = _norm(_normalize_korean_numbers(hyp))
            dist_num = _levenshtein(ref_num, hyp_num)
            denom_num = max(1, len(ref_num))
            cer_num = dist_num / denom_num
            rows.append(
                {
                    "id": idx,
                    "session_id": session_id,
                    "reference_text": phrase,
                    "hypothesis_text": hyp,
                    "reference_norm": ref_n,
                    "hypothesis_norm": hyp_n,
                    "edit_distance": dist,
                    "char_error_rate": round(cer, 6),
                    "char_accuracy": round(max(0.0, 1.0 - cer), 6),
                    "reference_norm_number_aware": ref_num,
                    "hypothesis_norm_number_aware": hyp_num,
                    "edit_distance_number_aware": dist_num,
                    "char_error_rate_number_aware": round(cer_num, 6),
                    "char_accuracy_number_aware": round(max(0.0, 1.0 - cer_num), 6),
                    "decode_ms": hyp_doc.get("decode_ms"),
                    "audio_duration_ms": hyp_doc.get("audio_duration_ms"),
                    "wav_path": str(wav_path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
        except Exception as exc:  # noqa: BLE001
            failures.append(f"phrase_{idx}:{exc}")

    avg_acc = round(sum(r["char_accuracy"] for r in rows) / len(rows), 6) if rows else 0.0
    avg_cer = round(sum(r["char_error_rate"] for r in rows) / len(rows), 6) if rows else 1.0
    min_acc = round(min((r["char_accuracy"] for r in rows), default=0.0), 6)
    max_acc = round(max((r["char_accuracy"] for r in rows), default=0.0), 6)
    avg_acc_num = (
        round(sum(r["char_accuracy_number_aware"] for r in rows) / len(rows), 6) if rows else 0.0
    )
    avg_cer_num = (
        round(sum(r["char_error_rate_number_aware"] for r in rows) / len(rows), 6) if rows else 1.0
    )
    min_acc_num = round(min((r["char_accuracy_number_aware"] for r in rows), default=0.0), 6)
    max_acc_num = round(max((r["char_accuracy_number_aware"] for r in rows), default=0.0), 6)

    out = {
        "schema": "sherpa_onnx_stt_ko_phrase_benchmark_v1",
        "lane": "b_track_hypo",
        "generated_at_utc": _utc_now(),
        "rows": rows,
        "rows_ok": len(rows),
        "rows_failed": len(failures),
        "failures": failures,
        "phrase_count_target": len(PHRASES),
        "char_accuracy_avg": avg_acc,
        "char_accuracy_min": min_acc,
        "char_accuracy_max": max_acc,
        "char_error_rate_avg": avg_cer,
        "char_accuracy_number_aware_avg": avg_acc_num,
        "char_accuracy_number_aware_min": min_acc_num,
        "char_accuracy_number_aware_max": max_acc_num,
        "char_error_rate_number_aware_avg": avg_cer_num,
        "number_aware_delta_accuracy_avg": round(avg_acc_num - avg_acc, 6),
        "disclaimer": "research_only",
        "reproduce": "py scripts/run_sherpa_onnx_stt_ko_phrase_benchmark_v1.py",
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(OUT), "rows_ok": len(rows), "char_accuracy_avg": avg_acc}, ensure_ascii=False))
    return 0 if rows else 1


if __name__ == "__main__":
    raise SystemExit(main())
