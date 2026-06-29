#!/usr/bin/env python3
"""Local M1 guardrail PoC: regex redaction -> masked bridge request (B-track, research_only)."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.fetch_pet_companion_device_bridge_live_v1 import (  # noqa: E402
    build_bridge_request,
)

DEFAULT_SAMPLE = (
    "홍길동님 연락처 010-1234-5678, 경기도 광명시 하안동 동물병원에서 "
    "치료비 50만 원 견적을 받았어요. 우리 토이푸들 초코가 산책 후 다리를 불편해합니다."
)
DEFAULT_BRIDGE_OUT = ROOT / "reports/tmp/pet_companion_bridge_request_poc_latest.json"
DEFAULT_BENCH_OUT = ROOT / "reports/edge_m1_guardrail_bench_latest.json"
DEFAULT_REDACTION_OUT = ROOT / "reports/local_guardrail_m1_poc_latest.json"


@dataclass(frozen=True)
class PiiPattern:
    pattern_id: str
    regex: re.Pattern[str]
    replacement: str


PII_PATTERNS: tuple[PiiPattern, ...] = (
    PiiPattern("phone_kr", re.compile(r"\d{2,3}-\d{3,4}-\d{4}"), "[PHONE]"),
    PiiPattern("address_hint", re.compile(r"경기도\s*광명시|하안동|동물병원"), "[ADDRESS]"),
    PiiPattern("money_kr", re.compile(r"\d+\s*만\s*원"), "[MONEY]"),
    PiiPattern("name_demo", re.compile(r"홍길동"), "[NAME]"),
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def apply_m1_redaction(text: str) -> tuple[str, list[dict[str, Any]]]:
    masked = text
    hits: list[dict[str, Any]] = []
    for pat in PII_PATTERNS:
        found = pat.regex.findall(masked)
        if not found:
            continue
        masked = pat.regex.sub(pat.replacement, masked)
        hits.append({"pattern_id": pat.pattern_id, "count": len(found)})
    return masked.strip(), hits


def build_poc_document(
    *,
    raw_text: str,
    profile_id: str,
    scenario: str,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    masked, hits = apply_m1_redaction(raw_text)
    latency_ms = (time.perf_counter() - t0) * 1000.0
    raw_b = raw_text.encode("utf-8")
    masked_b = masked.encode("utf-8")
    slots = [
        {
            "subject": profile_id,
            "fact_summary": masked[:100],
            "confidence_tier": "SLOT_INFERRED",
        }
    ]
    bridge = build_bridge_request(
        profile_id=profile_id,
        scenario=scenario,
        question_masked=masked,
        extracted_slots=slots,
    )
    bridge["request_id"] = f"req-m1-{uuid.uuid4().hex[:12]}"
    bridge["client_ts_utc"] = _utc_now()
    return {
        "schema": "local_guardrail_m1_poc_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "non_gating": True,
        "redaction_profile_id": "pii_mask_v1",
        "raw_text_len": len(raw_text),
        "masked_text_len": len(masked),
        "pii_pattern_hits": hits,
        "latency_ms": round(latency_ms, 3),
        "bridge_request": bridge,
    }


def build_bench_document(*, poc: dict[str, Any], raw_text: str) -> dict[str, Any]:
    masked = str((poc.get("bridge_request") or {}).get("raw_user_question_masked") or "")
    raw_b = len(raw_text.encode("utf-8"))
    masked_b = len(masked.encode("utf-8"))
    ratio = 1.0 - (masked_b / raw_b) if raw_b else 0.0
    return {
        "schema": "edge_m1_guardrail_bench_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "latency_ms": poc.get("latency_ms", 0),
        "raw_utf8_bytes": raw_b,
        "masked_utf8_bytes": masked_b,
        "mask_byte_ratio": round(max(0.0, min(1.0, ratio)), 4),
        "pii_pattern_hits": poc.get("pii_pattern_hits") or [],
        "track_wall": {
            "note": "Bench only; not Track A compression KPI or commercial LLM Final.",
        },
    }


def _load_input_text(args: argparse.Namespace) -> str:
    if args.text:
        return args.text.strip()
    if args.stdin_json:
        raw = sys.stdin.read()
        if not raw.strip():
            return DEFAULT_SAMPLE
        obj = json.loads(raw)
        if isinstance(obj, dict):
            for key in ("raw_user_question", "text", "user_question"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
        return DEFAULT_SAMPLE
    if args.input_json and Path(args.input_json).is_file():
        obj = json.loads(Path(args.input_json).read_text(encoding="utf-8-sig"))
        if isinstance(obj, dict):
            for key in ("raw_user_question", "text", "user_question"):
                val = obj.get(key)
                if isinstance(val, str) and val.strip():
                    return val.strip()
    return DEFAULT_SAMPLE


def main() -> int:
    ap = argparse.ArgumentParser(description="Local M1 guardrail PoC (B-track)")
    ap.add_argument("--text", help="Raw user text to redact")
    ap.add_argument("--stdin-json", action="store_true", help="Read JSON from stdin")
    ap.add_argument("--input-json", help="JSON file with raw_user_question")
    ap.add_argument("--profile-id", default="pet-demo-001")
    ap.add_argument("--scenario", default="health_check")
    ap.add_argument("--out-bridge", type=Path, default=DEFAULT_BRIDGE_OUT)
    ap.add_argument("--out-poc", type=Path, default=DEFAULT_REDACTION_OUT)
    ap.add_argument("--bench", action="store_true", help="Write edge_m1_guardrail_bench_latest.json")
    ap.add_argument("--bench-out", type=Path, default=DEFAULT_BENCH_OUT)
    args = ap.parse_args()

    raw_text = _load_input_text(args)
    poc = build_poc_document(
        raw_text=raw_text,
        profile_id=args.profile_id,
        scenario=args.scenario,
    )

    args.out_poc.parent.mkdir(parents=True, exist_ok=True)
    args.out_bridge.parent.mkdir(parents=True, exist_ok=True)
    args.out_poc.write_text(json.dumps(poc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.out_bridge.write_text(
        json.dumps(poc["bridge_request"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    if args.bench:
        bench = build_bench_document(poc=poc, raw_text=raw_text)
        args.bench_out.parent.mkdir(parents=True, exist_ok=True)
        args.bench_out.write_text(json.dumps(bench, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"ok": True, "bench_out": str(args.bench_out)}, ensure_ascii=False))

    print(
        json.dumps(
            {
                "ok": True,
                "bridge_out": str(args.out_bridge),
                "poc_out": str(args.out_poc),
                "pii_hits": poc.get("pii_pattern_hits"),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
