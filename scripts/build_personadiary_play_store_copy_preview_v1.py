#!/usr/bin/env python3
"""Build PersonaDiary Play Store copy preview v1 (PUBLIC_FACING + preview_only)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "docs/final/artifacts/personadiary_play_store_copy_preview_v1_latest.json"
COPY_CONTRACT = ROOT / "docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_doc() -> dict:
    contract = {}
    if COPY_CONTRACT.is_file():
        contract = json.loads(COPY_CONTRACT.read_text(encoding="utf-8"))
    _ = contract.get("anchor_line_ko", "")
    return {
        "schema": "personadiary_play_store_copy_preview_v1",
        "preview_only": True,
        "research_only": True,
        "send_gate_default": "HOLD",
        "short_description_ko": "찰나의 나라 — 오늘 마음·리듬 성찰 일기 (예언·투자 조언 아님)",
        "full_description_ko": (
            "Persona Diary는 하루를 짧게 정리하는 성찰 일기입니다.\n\n"
            "• 찰나(moment) 질문과 일일 카드로 오늘의 흐름을 기록\n"
            "• 기기 안에만 저장되는 Pull-first 일기 (preview_only)\n"
            "• Intent로 메모·리마인더를 빠르게 적재 (OS 원격제어 아님)\n\n"
            "본 앱은 운세·적중·투자·의료 조언을 제공하지 않습니다. "
            "mkmlife 결제·데이터와 합쳐지지 않습니다. "
            "연구 미리보기 단계이며 SEND_GATE: HOLD입니다."
        ),
        "disclaimer_ko": (
            "preview_only · research_only · 예언·적중·%·운세 단정 없음 · "
            "투자·임상·실매매 조언 없음 · mkmlife·Track A 합선 없음"
        ),
        "forbidden_claims_ack": "no hit rate · no prophecy · no OS app blocking claims in v0.9",
        "boundary_ack": contract.get(
            "native_shell_boundary_ack",
            "non_prediction_copy_contract_v1 · Capacitor WebView · no Track A join",
        ),
        "public_facing_pointer": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
        "copy_contract_pointer": "docs/final/artifacts/personadiary_non_prediction_copy_contract_v1_latest.json",
        "generated_at_utc": _utc_now(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--stdout", action="store_true")
    args = parser.parse_args()

    doc = build_doc()
    # drop optional null
    doc = {k: v for k, v in doc.items() if v is not None}
    text = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    if args.stdout:
        sys.stdout.write(text)
    else:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(text, encoding="utf-8")
        print(f"WROTE: {args.out_json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
