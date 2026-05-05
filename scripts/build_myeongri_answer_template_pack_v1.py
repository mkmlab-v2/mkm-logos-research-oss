# -*- coding: utf-8 -*-
"""Build standardized MKM Myeongri answer templates (ko/en) by profile."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "final" / "artifacts" / "myeongri_answer_template_pack_latest.json"


def _template(profile: str, lang: str) -> str:
    if lang == "ko":
        return (
            "[입력 요약]\n"
            "- birth_instant_utc / iana_tz / as_of_utc: {input_summary}\n\n"
            "[결정론 근거]\n"
            "- artifact_paths: {artifact_paths}\n"
            "- 핵심 필드: {deterministic_fields}\n\n"
            "[명리 해석 - HYPO]\n"
            "- 프로파일({profile}) 기준 가설: {hypothesis_block}\n\n"
            "[멀티렌즈 정렬]\n"
            "- Field -> Lens(사상/명리/성경[NON_GATING]) -> Conflict -> Final Action\n\n"
            "[경계]\n"
            "- 본 출력은 B-track 해석 보조이며 실매매/의료/교리 최종판정이 아님."
        )
    return (
        "[Input Summary]\n"
        "- birth_instant_utc / iana_tz / as_of_utc: {input_summary}\n\n"
        "[Deterministic Anchors]\n"
        "- artifact_paths: {artifact_paths}\n"
        "- key fields: {deterministic_fields}\n\n"
        "[Myeongri Interpretation - HYPO]\n"
        "- profile({profile}) hypothesis: {hypothesis_block}\n\n"
        "[Multi-lens Alignment]\n"
        "- Field -> Lens(Sasang/Myeongri/Logos[NON_GATING]) -> Conflict -> Final Action\n\n"
        "[Boundary]\n"
        "- B-track narrative support only; not a live trading, medical, or doctrinal final decision."
    )


def build_payload() -> dict:
    profiles = ["general", "daewoon", "ten-gods", "yongsin", "career", "llm-benchmark", "landscape"]
    templates = []
    for p in profiles:
        templates.append({"profile": p, "lang": "ko", "template": _template(p, "ko")})
        templates.append({"profile": p, "lang": "en", "template": _template(p, "en")})
    return {
        "schema": "myeongri_answer_template_pack_v1",
        "version": "1.0.0",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "policy_note": "Template-only pack. Fill placeholders from deterministic artifacts and validated envelope context.",
        "templates": templates,
    }


def main() -> int:
    payload = build_payload()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"written={OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
