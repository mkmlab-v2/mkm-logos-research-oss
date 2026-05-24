"""O-P31c public audio copy guard — sanitize + forbidden-term scan (Zone B)."""

from __future__ import annotations

import re
from typing import List, Tuple

DISCLAIMER_REQUIRED_SNIPPETS = ("투자", "의료", "법률", "자문", "아닙")

DISCLAIMER_TEXT_KO = (
    "본 방송은 투자, 의료, 법률 자문이 아닙니다. "
    "다중 렌즈 해설은 관측·페이싱 참고용이며, 실전 결정은 청취자 본인에게 있습니다."
)

CLOSING_CTA_KO = "오늘의 리듬·원퀘스천은 mkmlife.com 에서 이어집니다. 편안한 하루 되십시오."

_FORBIDDEN_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
    ("price_decimal_pct", re.compile(r"\d{1,3}(?:\.\d+)?\s*%")),
    ("large_integer", re.compile(r"\b\d{5,}\b")),
    ("hit_rate_pct", re.compile(r"57\.3|47\.5|적중률\s*\d")),
    ("order_verb", re.compile(r"매수|매도|풀매수|공매도|목표가|손절가")),
    ("ticker_price", re.compile(r"(?:BTC|비트코인|코스피|나스닥).{0,12}\d{3,}", re.I)),
    ("usd_krw_amount", re.compile(r"(?:USD|KRW|원)\s*[\d,]{4,}", re.I)),
    # Zone B science narrative — no deterministic physics/medical claims (FAIL-GUARD-009)
    ("science_quantum_proof", re.compile(r"양자역학으로\s*(?:입증|증명|확정)")),
    ("science_afterlife", re.compile(r"사후세계\s*(?:존재|입증|확인|증명)")),
    ("science_microtubule_cure", re.compile(r"미세소관이\s*(?:치료|완치)")),
    ("science_anesthesia_replace", re.compile(r"전신마취를\s*(?:대체|유도)")),
    ("science_medical_proof", re.compile(r"의학적으로\s*(?:입증|공인)")),
    ("science_neuro_guarantee", re.compile(r"신경과학적으로\s*(?:증명|입증|보장)")),
]

_SANITIZE_PATTERNS: List[Tuple[re.Pattern[str], str]] = [
    (re.compile(r"\d{5,}(?:\.\d+)?"), "[관측밴드]"),
    (re.compile(r"\d{1,3}(?:\.\d+)?\s*%"), "흐름 지표"),
    (re.compile(r"57\.3\s*%|47\.5\s*%|적중률\s*[\d.]+\s*%"), ""),
    (re.compile(r"O-P29b|O-P30|O-P31\w*", re.I), ""),
    (re.compile(r"\bBTC[- ]?USD\b", re.I), "글로벌 자산"),
    (re.compile(r"\bbtc\b", re.I), "글로벌 자산"),
    (re.compile(r"실매매|Track A|track_a", re.I), "운영 게이트"),
    (re.compile(r"소음인|태음인|태양인|소양인(?=\s*성향)", re.I), "편향 패턴"),
]


def sanitize_public_audio_text(text: str) -> str:
    out = (text or "").strip()
    for pat, repl in _SANITIZE_PATTERNS:
        out = pat.sub(repl, out)
    out = re.sub(r"\s{2,}", " ", out).strip()
    return out


def scan_forbidden(text: str) -> List[str]:
    hits: List[str] = []
    for name, pat in _FORBIDDEN_PATTERNS:
        if pat.search(text or ""):
            hits.append(name)
    return hits


def disclaimer_ok(text: str) -> bool:
    t = text or ""
    return all(s in t for s in DISCLAIMER_REQUIRED_SNIPPETS)
