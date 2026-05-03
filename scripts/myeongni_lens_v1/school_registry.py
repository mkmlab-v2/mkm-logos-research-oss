from __future__ import annotations

import hashlib
import json
import math
from typing import Any

# 확장 포인트: 신규 학파는 이 맵에 등록 후 스코어러 추가.
KNOWN_SCHOOL_IDS: frozenset[str] = frozenset(
    {
        "zi_ping",
        "zi_wei",
        "blindman_stub",
        "mkm_coordinator_default",
    }
)

DEFAULT_COORDINATOR_WEIGHTS: dict[str, float] = {
    "zi_ping": 0.35,
    "zi_wei": 0.35,
    "blindman_stub": 0.15,
    "mkm_coordinator_default": 0.15,
}


def _hash_to_unit_interval(key: str) -> float:
    h = hashlib.sha256(key.encode("utf-8")).digest()
    u = int.from_bytes(h[:8], "big") / float(2**64)
    return u * 2.0 - 1.0  # [-1, 1]


def score_school_stub(school_id: str, context: dict[str, Any]) -> dict[str, Any]:
    """
    학파별 스텁: 실제 명리 엔진 연결 전까지 입력 지문으로 결정론적 방향 힌트만 생성.
    context: pillars, dayun_index, sinsal_ids 등 advanced_input 조각.
    """
    pillars = context.get("pillars") or {}
    canon = _json_canon({"school": school_id, "pillars": pillars})
    base = _hash_to_unit_interval(canon)
    damp = 0.55
    direction_hint = max(-1.0, min(1.0, base * damp))

    return {
        "school_id": school_id,
        "direction_hint": round(direction_hint, 6),
        "confidence_hint": round(0.35 + 0.45 * (1.0 - abs(direction_hint)), 6),
        "method": "deterministic_stub_v1",
    }


def _json_canon(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def normalize_weights(raw: dict[str, float] | None, schools_requested: list[str]) -> dict[str, float]:
    if not raw:
        w = {k: DEFAULT_COORDINATOR_WEIGHTS.get(k, 0.0) for k in schools_requested}
    else:
        w = {k: float(v) for k, v in raw.items() if k in KNOWN_SCHOOL_IDS}
    s = sum(max(0.0, v) for v in w.values())
    if s <= 0.0:
        n = max(1, len(schools_requested))
        return {k: 1.0 / n for k in schools_requested}
    return {k: max(0.0, v) / s for k, v in w.items()}


def blend_school_direction(
    school_signals: list[dict[str, Any]],
    weights: dict[str, float],
) -> tuple[float, float]:
    """가중 평균 direction_hint / confidence_hint."""
    if not school_signals:
        return 0.0, 0.35
    num = 0.0
    d_w = 0.0
    c_num = 0.0
    c_w = 0.0
    for sig in school_signals:
        sid = str(sig.get("school_id") or "")
        wi = float(weights.get(sid, 0.0))
        if wi <= 0.0:
            continue
        d = float(sig.get("direction_hint") or 0.0)
        c = float(sig.get("confidence_hint") or 0.5)
        num += d * wi
        d_w += wi
        c_num += c * wi
        c_w += wi
    if d_w <= 0.0:
        return 0.0, 0.35
    dir_out = max(-1.0, min(1.0, num / d_w))
    conf_out = max(0.05, min(0.95, c_num / c_w if c_w > 0 else 0.35))
    return dir_out, conf_out


def math_blend_v0_and_schools(
    direction_v0: float,
    confidence_v0: float,
    direction_schools: float,
    confidence_schools: float,
    *,
    alpha_v0: float = 0.65,
) -> tuple[float, float]:
    """v0 실험 스트림과 학파 블렌드 (alpha: v0 비중)."""
    a = max(0.0, min(1.0, alpha_v0))
    d = a * direction_v0 + (1.0 - a) * direction_schools
    c = math.sqrt(max(0.0, a * confidence_v0**2 + (1.0 - a) * confidence_schools**2))
    return max(-1.0, min(1.0, d)), max(0.05, min(0.95, c))
