"""TKM health 24h skin — stricter non-clinical copy guard (Zone B)."""

from __future__ import annotations

import re
from typing import List, Tuple

from scripts.mkm_radio_dialogue_guard_v1 import (  # noqa: E402
    _SANITIZE_PATTERNS,
    sanitize_public_audio_text,
)

DISCLAIMER_REQUIRED_SNIPPETS = ("진료", "처방", "참고", "의료")

DISCLAIMER_TEXT_KO = (
    "본 방송은 진료·처방이 아닙니다. "
    "전통 리듬·생활 습관은 참고용이며, 증상이 있으면 의료기관을 방문하십시오."
)

CLOSING_CTA_KO = (
    "오늘의 생활 리듬·웰니스 참고는 mkmlife.com 에서 이어집니다. 편안한 하루 되십시오."
)

_HEALTH_FORBIDDEN: List[Tuple[str, re.Pattern[str]]] = [
    ("prescription", re.compile(r"처방|처방전|복용량|mg\s*복용|일일\s*\d+정")),
    ("diagnosis_claim", re.compile(r"진단합니다|확진|병명은|질병명|(?:암|당뇨|고혈압)\s*입니다")),
    ("cure_efficacy", re.compile(r"완치|치료\s*효과|효능\s*\d|100\s*%|치료됩니다")),
    ("constitution_fix", re.compile(r"(?:태양|소양|태음|소음)인\s*(?:체질|확정|입니다)")),
    ("herbal_rx", re.compile(r"한약|탕약|처방\s*한|약재\s*복용")),
    ("surgery_advice", re.compile(r"수술\s*권|입원\s*하|시술\s*받")),
]

_MKM_FORBIDDEN_IMPORT = None


def _mkm_patterns() -> List[Tuple[str, re.Pattern[str]]]:
    global _MKM_FORBIDDEN_IMPORT
    if _MKM_FORBIDDEN_IMPORT is None:
        from scripts.mkm_radio_dialogue_guard_v1 import _FORBIDDEN_PATTERNS

        _MKM_FORBIDDEN_IMPORT = _FORBIDDEN_PATTERNS
    return _MKM_FORBIDDEN_IMPORT


def scan_forbidden(text: str) -> List[str]:
    hits: List[str] = []
    for name, pat in _HEALTH_FORBIDDEN + _mkm_patterns():
        if pat.search(text or ""):
            hits.append(name)
    return hits


def disclaimer_ok(text: str) -> bool:
    t = text or ""
    return all(s in t for s in DISCLAIMER_REQUIRED_SNIPPETS)


def sanitize_health_audio_text(text: str) -> str:
    out = sanitize_public_audio_text(text)
    for pat, repl in _SANITIZE_PATTERNS:
        out = pat.sub(repl, out)
    out = re.sub(r"닥터\s*사상", "코칭 사상", out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out
