#!/usr/bin/env python3
"""Assemble defense_pitch_codepack_v1.json from defense_code_pack_v1 + MKM12 (+ optional ATHENA).

Outputs machine-readable pack for translator system prompts. Does not replace human review.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_BASE = ROOT / "docs/final/artifacts/defense_code_pack_v1.json"
DEFAULT_MKM12 = ROOT / "docs/final/MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md"
DEFAULT_ATHENA_EXT = ROOT / "docs/final/ATHENA_AUDITOR_REALITY_ALIGNED_EXTERNAL_V1_2026-04-09.md"
DEFAULT_BRIEFING = ROOT / "docs/final/artifacts/DEFENSE_BENCH_BRIEFING_BULLETS_V1.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/defense_pitch_codepack_v1.json"

_PATH_RE = re.compile(r"`(docs/[^`]+\.(?:md|json))`")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_mkm12_paths(md: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _PATH_RE.finditer(md):
        p = m.group(1).replace("\\", "/")
        if p not in seen:
            seen.add(p)
            out.append(p)
    return sorted(out)


def _parse_mkm12_tag_lines(md: str, tag: str) -> list[str]:
    """First line of each bullet starting with '- [TAG]' (trimmed, max 500 chars)."""
    lines = md.splitlines()
    out: list[str] = []
    prefix = f"- [{tag}]"
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith(prefix):
            block = s
            j = i + 1
            while j < len(lines) and lines[j].strip().startswith("- ") and not lines[j].strip().startswith("- ["):
                block += " " + lines[j].strip()
                j += 1
            out.append(block[:500])
    return out[:80]


def _lexicon_kv_rows(base: dict[str, Any]) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for row in base.get("terminology_translation_matrix") or []:
        src = str(row.get("internal_or_forbidden_in_external") or "")
        tgt_ko = str(row.get("defense_facing_ko") or "")
        tgt_en = str(row.get("defense_facing_en") or "")
        rule = str(row.get("rule") or "")
        out.append(
            {
                "source": src,
                "target_ko": tgt_ko,
                "target_en": tgt_en,
                "rule": rule or "대외 문서에서 source 표현을 target으로 치환 또는 설명 대체.",
            }
        )
    return out


def _merge_forbidden(base: dict[str, Any], mkm12_md: str) -> list[str]:
    existing = list(base.get("claim_boundaries", {}).get("forbidden_external_phrases") or [])
    # MKM12에서 반복되는 위험 표현 — 문서에 등장 시에만 추가 (중복 제거)
    candidates = [
        "100% 무손실 복원",
        "RS/ECC 완전 적용",
        "NotebookLM 브리핑 단독 근거",
    ]
    seen = set(existing)
    for e in candidates:
        if e not in seen and e in mkm12_md:
            seen.add(e)
            existing.append(e)
    return existing


def _read_optional(path: Path) -> tuple[str | None, bool]:
    if not path.is_file():
        return None, False
    return path.read_text(encoding="utf-8"), True


def build_pitch_pack(
    *,
    base: dict[str, Any],
    mkm12_text: str,
    athena_text: str | None,
    athena_present: bool,
    briefing_doc: dict[str, Any] | None,
    briefing_path_for_sources: str,
) -> dict[str, Any]:
    warnings: list[str] = []
    if not athena_present:
        warnings.append(
            "Missing optional source: docs/final/ATHENA_AUDITOR_REALITY_ALIGNED_EXTERNAL_V1_2026-04-09.md — using MKM12 + base only."
        )
    if briefing_doc is None:
        warnings.append(
            "Missing DEFENSE_BENCH_BRIEFING_BULLETS_V1.json — run scripts/build_defense_bench_briefing_bullets.py after snapshot."
        )

    cb = base.get("claim_boundaries") or {}
    merged_forbidden = _merge_forbidden(base, mkm12_text)

    pitch: dict[str, Any] = {
        "schema": "defense_pitch_codepack_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "purpose": "국방 대외·번역기 시스템 프롬프트 주입용 단일 JSON. FACT/HYPO 경계와 용어 치환을 기계적으로 고정한다.",
        "build": {
            "script": "scripts/build_defense_codepack.py",
            "sources": {
                "base_code_pack": "docs/final/artifacts/defense_code_pack_v1.json",
                "mkm12_claims_md": "docs/final/MKM12_L0_L1_L2_CLAIMS_TAGGED_FACTCHECK_2026-04-09.md",
                "athena_external_md": "docs/final/ATHENA_AUDITOR_REALITY_ALIGNED_EXTERNAL_V1_2026-04-09.md",
                "athena_loaded": athena_present,
                "briefing_bullets_json": briefing_path_for_sources if briefing_doc else None,
            },
            "warnings": warnings,
        },
        "target_schema": {
            "uav_recon_synthetic_v1": (base.get("message_profiles") or {}).get("uav_recon_synthetic_v1"),
        },
        "lexicon_matrix": _lexicon_kv_rows(base),
        "claim_boundaries": {
            "tags": cb.get("tags"),
            "forbidden_external_phrases": merged_forbidden,
            "required_citation_style": cb.get("required_citation_style"),
            "aligned_docs": cb.get("aligned_docs"),
            "mkm12_fact_line_samples": _parse_mkm12_tag_lines(mkm12_text, "FACT")[:24],
            "mkm12_hypo_line_samples": _parse_mkm12_tag_lines(mkm12_text, "HYPO")[:16],
        },
        "ssot_paths_from_mkm12": _parse_mkm12_paths(mkm12_text)[:40],
        "translator_system_prompt_injection": {
            "ko": _prompt_ko(),
            "en": _prompt_en(),
        },
    }
    bmvf = base.get("briefing_metaphors_vs_facts")
    if isinstance(bmvf, dict) and bmvf:
        pitch["briefing_metaphors_vs_facts"] = bmvf
    tass = base.get("track_a_headline_ssot")
    if isinstance(tass, dict) and tass:
        pitch["track_a_headline_ssot"] = tass
    if athena_text:
        pitch["athena_external_excerpt"] = {
            "chars": len(athena_text),
            "first_lines": "\n".join(athena_text.splitlines()[:40]),
        }
    if briefing_doc:
        pitch["briefing_bullets"] = {
            "schema": briefing_doc.get("schema"),
            "generated_at_utc": briefing_doc.get("generated_at_utc"),
            "sources": briefing_doc.get("sources"),
            "briefing_bullets_ko": briefing_doc.get("briefing_bullets_ko"),
            "briefing_bullets_en": briefing_doc.get("briefing_bullets_en"),
        }
    return pitch


def _prompt_ko() -> str:
    return (
        "당신은 국방 대외 제안서·기술 요약 번역/편집 보조다. "
        "내부 연구명(게마트리아·사원수·4D 내부 축명·명리)을 대외 문서에 그대로 노출하지 말고 lexicon_matrix의 target_ko로 치환하거나 공학적 설명으로 대체한다. "
        "forbidden_external_phrases에 포함된 표현을 생성하지 않는다. "
        "수치 주장은 반드시 SSOT JSON 경로를 요구하며 [FACT]로만 단정한다. "
        "HYPO/VISION은 '가설' '연구 목표'로 명시한다."
    )


def _prompt_en() -> str:
    return (
        "You assist with defense-facing technical prose. "
        "Never expose internal research codenames (gematria, quaternion axes, Myeongri) in external documents; "
        "use lexicon_matrix target_en or neutral engineering language. "
        "Do not output phrases listed in forbidden_external_phrases. "
        "Numeric claims require artifact paths; state hypotheses as hypotheses."
    )


def main() -> int:
    ap = argparse.ArgumentParser(description="Build defense_pitch_codepack_v1.json")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--mkm12", type=Path, default=DEFAULT_MKM12)
    ap.add_argument("--athena-external", type=Path, default=DEFAULT_ATHENA_EXT)
    ap.add_argument("--briefing", type=Path, default=DEFAULT_BRIEFING, help="DEFENSE_BENCH_BRIEFING_BULLETS_V1.json")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    base = _load_json(args.base)
    mkm12_text = args.mkm12.read_text(encoding="utf-8")
    athena_text, athena_ok = _read_optional(args.athena_external)
    briefing_doc: dict[str, Any] | None = None
    briefing_rel = "docs/final/artifacts/DEFENSE_BENCH_BRIEFING_BULLETS_V1.json"
    if args.briefing.is_file():
        briefing_doc = _load_json(args.briefing)

    pitch = build_pitch_pack(
        base=base,
        mkm12_text=mkm12_text,
        athena_text=athena_text,
        athena_present=athena_ok,
        briefing_doc=briefing_doc,
        briefing_path_for_sources=briefing_rel,
    )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(pitch, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out}")
    for w in pitch["build"]["warnings"]:
        print(f"WARNING: {w}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
