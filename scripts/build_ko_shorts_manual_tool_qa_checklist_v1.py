#!/usr/bin/env python3
"""CapCut/Vrew manual QA checklist for ko shorts STT pipeline [HYPO]."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/ko_shorts_manual_tool_qa_checklist_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def build_manual_tool_qa_checklist_v1() -> dict[str, Any]:
    burnin_batch = ROOT / "reports/ko_shorts_burnin_batch_v1_latest.json"
    gate_bench = ROOT / "reports/ko_shorts_subtitle_gate_bench_v1_latest.json"
    compare = ROOT / "reports/ko_shorts_timing_compare_v1_latest.json"

    mp4_refs = [
        "reports/ko_shorts_burnin_web_deeply_v1_latest.mp4",
        "reports/ko_shorts_burnin_web_pansori_v1_latest.mp4",
        "reports/ko_shorts_burnin_web_youtube_edu_v1_latest.mp4",
    ]

    checklist = [
        {
            "id": "sync_drift",
            "tool": "Cursor IDE browser + ffmpeg",
            "prompt": "자막 시작/끝이 발화와 0.3s 이내인가? (P1 aligned 기준)",
            "pass_threshold": "p1_anchor_sync auto_pass + profile_parent_span",
            "artifact": "reports/ko_shorts_cursor_ide_qa_v1_latest.json",
        },
        {
            "id": "orphan_line",
            "tool": "Cursor IDE QA script",
            "prompt": "「첫째,」「줍니다.」만 단독 줄로 남는 고아 cue가 없는가?",
            "pass_threshold": "고아 0건",
            "artifact": "scripts/media_stt_transcription_lib_v1.py semantic_chunk_ko_v1",
        },
        {
            "id": "netflix_cpl",
            "tool": "Cursor IDE QA script",
            "prompt": "한 줄 16자(공백 포함) 초과 cue가 없는가?",
            "pass_threshold": "netflix_v16 gate_pass",
            "artifact": _rel(gate_bench) if gate_bench.is_file() else None,
        },
        {
            "id": "safe_area",
            "tool": "Cursor IDE browser preview",
            "prompt": "하단 UI(좋아요·댓글)와 자막 겹침 없는가?",
            "pass_threshold": "safe_area_frames bright_ratio + ASS MarginV",
            "artifact": "reports/ko_shorts_cursor_preview_v1.html",
        },
        {
            "id": "cps_readability",
            "tool": "Cursor IDE QA script",
            "prompt": "12 CPS 이하로 읽기 편한가? (빠른 실연설은 예외 메모)",
            "pass_threshold": "cps_hard <= 17; target <= 12",
            "artifact": _rel(gate_bench) if gate_bench.is_file() else None,
        },
        {
            "id": "scholarly_mode_isolation",
            "tool": "reviewer",
            "prompt": "학술 YT ingest(650+자 merge)와 쇼츠 STT 체인이 혼용되지 않았는가?",
            "pass_threshold": "별도 SSOT·pytest guard",
            "artifact": "tests/test_ko_shorts_scholarly_mode_guard_v1.py",
        },
    ]

    return {
        "schema": "ko_shorts_manual_tool_qa_checklist_v1",
        "research_only": True,
        "send_gate": "HOLD",
        "hypothesis_class": "HYPO",
        "generated_at_utc": _utc_now(),
        "purpose": "Manual CapCut/Vrew smoke — not automated superiority claim vs commercial tools",
        "checklist": checklist,
        "mp4_smoke_paths": mp4_refs,
        "reproduce": "powershell -File scripts/Invoke-KoShortsCursorIdeQa_v1.ps1",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    doc = build_manual_tool_qa_checklist_v1()
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": _rel(out), "items": len(doc["checklist"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
