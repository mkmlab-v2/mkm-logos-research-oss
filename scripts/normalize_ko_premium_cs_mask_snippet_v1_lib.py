"""Canonical ███ mask normalization for KO premium CS snippets (B-track).

Used by prospect patch + coverage wire-match for compression-v1 *-mask variants.
research_only · CS_MASK axis only.
"""

from __future__ import annotations

import re
from typing import Any

from scripts.extract_zone_ko_premium_cs_template_seeds_v1_lib import normalize_snippet

# Keep phone partial masks (010-****-1234) — production catalog kcs_t024 retains them.
_CANON_RULES: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"상담\s*진행\s*건"), "상담 건"),
    (re.compile(r"부탁드립니다"), "부탁합니다"),
    (re.compile(r"ORD-\S+"), "███"),
    (re.compile(r"4021-\*{4}-#+"), "███"),
    (re.compile(r"EDU-\*{4}-\d+"), "███"),
    (re.compile(r"이\*민 고객"), "███ 고객"),
    (re.compile(r"a\*\*\*@example\.com"), "███"),
    (re.compile(r"010-\*{4}-\d+ 로 요약"), "███ 으로 요약"),
]

MASK_FIX_SNIPPETS: dict[str, str] = {
    "kcs_p006": (
        "오늘 상담 건 정리 부탁합니다. ███ 고객 케이스요. ███ 으로 요약 메일 보내 주세요."
    ),
    "kcs_p019": (
        "환불 처리 관련하여 주문번호 ███ 환불 요청합니다. 이*민 명의 결제입니다. "
        "네, 고객님. 이*민 명의로 결제된 내역 확인 도와드리겠습니다. "
        "010-****-1234 로 연락 주세요. 대기 너무 깁니다."
    ),
    "kcs_p020": ("배송 조회해 보니 송장번호 ███ 건이 아직 안 왔어요. 한*별 담당 맞나요?"),
    "kcs_p021": (
        "강의 수강 취소했는데 환불 기한 지났다고 나옵니다. 시스템 오류 아닌가요? "
        "학습자 ID ███ 확인해 주세요."
    ),
}


def canonicalize_ko_cs_mask_snippet(snippet: str) -> str:
    out = normalize_snippet(snippet)
    for pat, repl in _CANON_RULES:
        out = pat.sub(repl, out)
    return out


def apply_mask_heuristics(snippet: str) -> str:
    """Best-effort ███ insertion for prospect rows still missing block mask after canon rules."""
    out = canonicalize_ko_cs_mask_snippet(snippet)
    if "███" in out:
        return out
    if "이*민 고객" in out:
        out = out.replace("이*민 고객", "███ 고객", 1)
    return normalize_snippet(out)


def resolve_ko_cs_catalog_match(
    snippet: str,
    catalog_rows: list[dict[str, Any]],
) -> tuple[str, None] | None:
    from scripts.compression_ko_premium_cs_deep_pack_v1_lib import resolve_template_match

    exact = resolve_template_match(snippet, catalog_rows)
    if exact:
        return exact
    if "███" in snippet:
        return None
    canon = canonicalize_ko_cs_mask_snippet(snippet)
    if canon == snippet:
        return None
    return resolve_template_match(canon, catalog_rows)
