# -*- coding: utf-8 -*-
"""명리 Track B — 지휘관 검토용 결정론 스냅샷(JSON). LLM 없음; fusion SSOT만 래핑."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.myeongri_complete_fusion import MyeongriCompleteFusion

ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT = ART / "myeongni_track_b_commander_report_latest.json"
ENVELOPE_PATH = ROOT / "data" / "myeongni" / "myeongni_track_b_commander_report_envelope_v1.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_envelope() -> dict[str, Any]:
    doc = json.loads(ENVELOPE_PATH.read_text(encoding="utf-8"))
    if doc.get("schema") != "myeongni_track_b_commander_report_envelope_v1":
        raise ValueError("envelope schema mismatch")
    return doc


def build_report_payload(
    *,
    birth_year: int,
    birth_month: int,
    birth_day: int,
    birth_hour: int,
    is_solar: bool,
    is_male: bool,
    precomputed_full_saju: dict[str, Any] | None,
    commander_notes: str | None = None,
) -> dict[str, Any]:
    env = load_envelope()
    fus = MyeongriCompleteFusion().calculate_complete_fusion(
        birth_year,
        birth_month,
        birth_day,
        birth_hour,
        is_solar=is_solar,
        is_male=is_male,
        precomputed_full_saju=precomputed_full_saju,
    )
    qiy = fus.get("daewoon_qiyun_v1") or {}
    handoff: dict[str, Any] = {
        "schema_contract": "myeongni_track_b_commander_report_v1",
        "notebooklm": {
            "manifest_pointer": "docs/NotebookLM_sources_manifest.md",
            "note_ko": "MCP 세션 주입 여부와 무관; 소스 추가는 지휘관 수동·정책 준수.",
        },
        "vault_optional": {
            "push_script_pointer": "scripts/push_local_artifacts_to_vault.ps1",
            "note_ko": "로컬 산출만 선별 동기화; 자동 본선 합선 없음.",
        },
    }
    return {
        "schema": "myeongni_track_b_commander_report_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc_now(),
        "labels": ["TRACK_B", "HYPO", "HUMAN_REVIEW_PENDING"],
        "commander_notes": commander_notes,
        "handoff": handoff,
        "envelope": {
            "schema": env.get("schema"),
            "version": env.get("version"),
            "source_track": env.get("source_track"),
            "hypothesis_tier": env.get("hypothesis_tier"),
            "human_review_required": env.get("human_review_required"),
            "disclaimer_ko": env.get("disclaimer_ko"),
            "core_axes": env.get("core_axes"),
        },
        "birth_input": {
            "year": birth_year,
            "month": birth_month,
            "day": birth_day,
            "hour": birth_hour,
            "is_solar": is_solar,
            "is_male": is_male,
            "precomputed_manseryeok": precomputed_full_saju is not None,
        },
        "axes_snapshot": {
            "four_pillars_ganji": fus.get("saju"),
            "surface_ohang_distribution": fus.get("ohang_strength"),
            "jijangan_weighted_ohang": fus.get("ohang_strength_jijangan_v1"),
            "vector_4d_surface": fus.get("vector_4d"),
            "vector_4d_jijangan_v1": fus.get("vector_4d_jijangan_v1"),
            "vector_4d_rule_school_v1": fus.get("vector_4d_rule_school_v1"),
            "rule_school_policy": fus.get("rule_school_mkm_4d_v1"),
            "daewoon_rows": fus.get("daewoon_v1"),
            "qiyun_meta": {
                "qiyun_years_float": qiy.get("qiyun_years_float"),
                "qiyun_days": qiy.get("qiyun_days"),
                "forward": qiy.get("forward"),
                "method": qiy.get("method"),
                "timezone": qiy.get("timezone"),
            },
            "jijangan_overlay": fus.get("jijangan_v1"),
        },
        "full_fusion_payload": fus,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--year", type=int, required=True)
    ap.add_argument("--month", type=int, required=True)
    ap.add_argument("--day", type=int, required=True)
    ap.add_argument("--hour", type=int, required=True)
    ap.add_argument("--male", action="store_true", help="남명(미설정 시 여명)")
    ap.add_argument("--solar", action="store_true", help="양력 플래그(만세력 인자)")
    ap.add_argument("--precomputed-json", type=Path, default=None, help="calculate_full_saju_perfect JSON")
    ap.add_argument(
        "--commander-notes",
        type=str,
        default="",
        help="지휘관 메모(비우면 null 저장)",
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    pre: dict[str, Any] | None = None
    if args.precomputed_json is not None:
        pre = json.loads(args.precomputed_json.read_text(encoding="utf-8"))

    notes_val: str | None = args.commander_notes.strip() or None
    payload = build_report_payload(
        birth_year=args.year,
        birth_month=args.month,
        birth_day=args.day,
        birth_hour=args.hour,
        is_solar=args.solar,
        is_male=args.male,
        precomputed_full_saju=pre,
        commander_notes=notes_val,
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"\nWROTE: {args.out}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
