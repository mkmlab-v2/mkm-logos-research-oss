"""[HYPO] B-track bridge v2 — multi-signal 4D (reports-only; not Track A SSOT)."""
from __future__ import annotations

import hashlib
import re
from typing import Mapping

SCRIPT_RE = re.compile(r"[\u0590-\u05FF\u0370-\u03FF\u1F00-\u1FFF]+")


def _hash_u32(*parts: str) -> int:
    blob = "|".join(parts).encode("utf-8")
    return int(hashlib.sha256(blob).hexdigest()[:8], 16)


def _lemma_sketch(text: str, k: int = 12) -> int:
    tokens = SCRIPT_RE.findall(text or "")
    if not tokens:
        return 0
    acc = 0
    for i, tok in enumerate(tokens[:k]):
        acc ^= _hash_u32(tok, str(i))
    return acc


def build_gematria_4d_bridge_v2_hypo(row: Mapping[str, object]) -> dict[str, float]:
    """Deterministic multi-channel 4D from verse row (no v1 mod-101 collapse)."""
    from tools.myeongni.gematria_myeongri_math_v1 import renorm_4d

    heb = int(row.get("hebrew_value") or 0)
    grk = int(row.get("greek_value") or 0)
    asc = int(row.get("ascii_value") or 0)
    vid = str(row.get("verse_id") or "")
    edition = str(row.get("edition") or "")
    text = str(row.get("original_text") or row.get("text") or "")

    vid_h = _hash_u32(vid)
    text_h = _hash_u32(text)
    lemma_h = _lemma_sketch(text)
    ed_h = _hash_u32(edition, vid)

    s_raw = (heb * 997 + vid_h % 1009 + 1) % 10007
    l_raw = (grk * 991 + (vid_h >> 12) % 1009 + 1) % 10007
    k_raw = (asc * 983 + text_h % 1009 + lemma_h % 503 + 1) % 10007
    m_raw = (lemma_h * 977 + ed_h % 503 + (text_h >> 8) % 251 + 1) % 10007

    total = float(s_raw + l_raw + k_raw + m_raw) or 1.0
    return renorm_4d(
        {
            "S": s_raw / total,
            "L": l_raw / total,
            "K": k_raw / total,
            "M": m_raw / total,
        }
    )
