#!/usr/bin/env py
"""Evaluate Sherpa STT smoke quality against Supertonic reference text (B-track)."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF_JSON = ROOT / "reports" / "supertonic_tts_btrack_smoke_v1_latest.json"
HYP_JSON = ROOT / "reports" / "sherpa_onnx_stt_btrack_smoke_v1_latest.json"
OUT_JSON = ROOT / "reports" / "sherpa_onnx_stt_quality_btrack_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _norm(text: str) -> str:
    t = text.strip().lower()
    t = re.sub(r"[^\w\uac00-\ud7a3]+", "", t)
    return t


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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ref", type=Path, default=REF_JSON)
    ap.add_argument("--hyp", type=Path, default=HYP_JSON)
    ap.add_argument("--out", type=Path, default=OUT_JSON)
    args = ap.parse_args()

    ref_doc = _read_json(args.ref)
    hyp_doc = _read_json(args.hyp)

    ref_text = str(ref_doc.get("sample_text") or "")
    hyp_text = str(hyp_doc.get("transcript") or "")

    ref_norm = _norm(ref_text)
    hyp_norm = _norm(hyp_text)
    dist = _levenshtein(ref_norm, hyp_norm)
    denom = max(1, len(ref_norm))
    cer = dist / denom

    out = {
        "schema": "sherpa_onnx_stt_quality_btrack_v1",
        "lane": "b_track_hypo",
        "generated_at_utc": _utc_now(),
        "reference_text": ref_text,
        "hypothesis_text": hyp_text,
        "reference_norm": ref_norm,
        "hypothesis_norm": hyp_norm,
        "edit_distance": dist,
        "reference_chars": len(ref_norm),
        "hypothesis_chars": len(hyp_norm),
        "char_error_rate": round(cer, 6),
        "char_accuracy": round(max(0.0, 1.0 - cer), 6),
        "decode_ms": hyp_doc.get("decode_ms"),
        "audio_duration_ms": hyp_doc.get("audio_duration_ms"),
        "runtime": hyp_doc.get("runtime"),
        "disclaimer": "research_only",
        "reproduce": "py scripts/evaluate_sherpa_onnx_stt_quality_btrack_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"out": str(args.out), "char_accuracy": out["char_accuracy"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
