#!/usr/bin/env python3
"""De-identified birth anchors for physician_gold TKM captures [HYPO]."""

from __future__ import annotations

from typing import Any

# Non-PHI synthetic anchors for B-track physician_gold only.
REF_TOKEN_BIRTH_ANCHORS: dict[str, dict[str, Any]] = {
    "ENC-PHYSICIAN-GOLD-AUTO-01": {
        "year": 1972,
        "month": 3,
        "day": 18,
        "hour": 9,
        "minute": 30,
        "iana_tz": "Asia/Seoul",
        "is_male": True,
    },
    "ENC-PHYSICIAN-GOLD-AUTO-02": {
        "year": 1968,
        "month": 11,
        "day": 2,
        "hour": 14,
        "minute": 0,
        "iana_tz": "Asia/Seoul",
        "is_male": False,
    },
    "ENC-PHYSICIAN-GOLD-AUTO-03": {
        "year": 1975,
        "month": 7,
        "day": 25,
        "hour": 6,
        "minute": 45,
        "iana_tz": "Asia/Seoul",
        "is_male": True,
    },
    "ENC-PHYSICIAN-GOLD-P21-01": {
        "year": 1971,
        "month": 5,
        "day": 9,
        "hour": 11,
        "minute": 15,
        "iana_tz": "Asia/Seoul",
        "is_male": False,
    },
    "ENC-DEMO-2026-0618-01": {
        "year": 1970,
        "month": 4,
        "day": 12,
        "hour": 15,
        "minute": 0,
        "iana_tz": "Asia/Seoul",
        "is_male": True,
    },
    "ENC-CLINIC-P19-01": {
        "year": 1965,
        "month": 6,
        "day": 22,
        "hour": 10,
        "minute": 0,
        "iana_tz": "Asia/Seoul",
        "is_male": True,
    },
    "PARK-GEUMJA-SENIOR-2026-001": {
        "year": 1943,
        "month": 2,
        "day": 1,
        "hour": 12,
        "minute": 0,
        "iana_tz": "Asia/Seoul",
        "is_male": False,
    },
}

DEFAULT_DEID_PROFILES: list[dict[str, Any]] = [
    {
        "year": 1970,
        "month": 4,
        "day": 12,
        "hour": 15,
        "minute": 0,
        "iana_tz": "Asia/Seoul",
        "is_male": True,
    },
    {
        "year": 1973,
        "month": 9,
        "day": 21,
        "hour": 8,
        "minute": 20,
        "iana_tz": "Asia/Seoul",
        "is_male": False,
    },
    {
        "year": 1969,
        "month": 12,
        "day": 5,
        "hour": 17,
        "minute": 10,
        "iana_tz": "Asia/Seoul",
        "is_male": True,
    },
    {
        "year": 1976,
        "month": 2,
        "day": 14,
        "hour": 13,
        "minute": 0,
        "iana_tz": "Asia/Seoul",
        "is_male": False,
    },
]


def resolve_birth_anchor(capture: dict[str, Any]) -> dict[str, Any] | None:
    meta = capture.get("meta") if isinstance(capture.get("meta"), dict) else {}
    explicit = meta.get("birth_anchor")
    if isinstance(explicit, dict) and explicit.get("year"):
        return dict(explicit)
    mods = capture.get("modalities_present") if isinstance(capture.get("modalities_present"), dict) else {}
    if mods.get("birth_profile") is not True and not explicit:
        return None
    enc = capture.get("encounter") if isinstance(capture.get("encounter"), dict) else {}
    ref = str(enc.get("ref_token") or "")
    if ref in REF_TOKEN_BIRTH_ANCHORS:
        return dict(REF_TOKEN_BIRTH_ANCHORS[ref])
    if ref:
        idx = abs(hash(ref)) % len(DEFAULT_DEID_PROFILES)
        return dict(DEFAULT_DEID_PROFILES[idx])
    return None


def engine_report_relpath(ref_token: str) -> str:
    safe = ref_token.replace("/", "_")[:80]
    return f"reports/myeongni_physician_gold_engine/{safe}_v1_latest.json"
