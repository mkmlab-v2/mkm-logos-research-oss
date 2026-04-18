#!/usr/bin/env python3
"""
KOSPI 사상 단독 레인 상용 게이트 JSON → BTC 전용 방어적 스트레스 (읽기 전용).

주문·시그널을 바꾸지 않고, `CryptoNitroLiveTrader`가 `macro_risk_level`과
`max()`로 합쳐 일일 거래 상한·`apply_macro_regime`에만 반영한다.
"""
from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, Mapping, Optional, Tuple, Union

logger = logging.getLogger(__name__)

WorkspaceRoot = Union[str, Path]

_DEFAULT_REL = Path("docs/final/artifacts/kospi_sasang_single_lane_commercial_gate_v1_latest.json")


def _as_path(root: WorkspaceRoot) -> Path:
    return Path(root).resolve()


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _floatish(v: Any) -> Optional[float]:
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    return None


def resolve_sasang_overlay(
    workspace_root: WorkspaceRoot,
    config: Optional[Mapping[str, Any]],
) -> Tuple[float, Dict[str, Any]]:
    """
    Returns:
        (stress, meta) — stress in [0, max_stress]; meta includes label, path, track.
    """
    root = _as_path(workspace_root)
    cfg = dict(config or {})
    overlay = cfg.get("kospi_sasang_btc_overlay")
    if not isinstance(overlay, dict):
        overlay = {}

    if overlay.get("enabled") is False:
        return 0.0, {
            "label": "disabled",
            "reason": "config_disabled",
            "path": None,
            "track": str(overlay.get("track") or "sasang_strict"),
        }

    max_stress = _floatish(overlay.get("max_stress"))
    if max_stress is None:
        max_stress = 0.45
    max_stress = _clamp(float(max_stress), 0.01, 1.0)

    track = str(overlay.get("track") or "sasang_strict")

    raw_path = (overlay.get("artifact_path") or "").strip()
    env_path = (os.getenv("MKM_KOSPI_SASANG_GATE_PATH") or "").strip()
    if raw_path:
        artifact = Path(raw_path).expanduser()
        if not artifact.is_absolute():
            artifact = (root / artifact).resolve()
    elif env_path:
        artifact = Path(env_path).expanduser().resolve()
    else:
        artifact = (root / _DEFAULT_REL).resolve()

    if not artifact.is_file():
        return 0.0, {
            "label": "disabled",
            "reason": "artifact_missing_or_invalid_json",
            "path": str(artifact),
            "track": track,
        }

    try:
        text = artifact.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, UnicodeError, json.JSONDecodeError) as e:
        logger.debug("사상 오버레이 JSON 읽기 실패: %s (%s)", artifact, e)
        return 0.0, {
            "label": "disabled",
            "reason": "artifact_missing_or_invalid_json",
            "path": str(artifact),
            "track": track,
        }

    if not isinstance(data, dict):
        return 0.0, {
            "label": "disabled",
            "reason": "artifact_missing_or_invalid_json",
            "path": str(artifact),
            "track": track,
        }

    stress = 0.0
    for key in ("fused_risk_pressure", "risk_pressure", "sasang_overlay_stress"):
        v = _floatish(data.get(key))
        if v is not None:
            stress = max(stress, _clamp(v, 0.0, 1.0))

    commercial_ready = data.get("commercial_ready")
    if commercial_ready is False:
        stress = max(stress, 0.22)

    gates = data.get("gates")
    g3: Dict[str, Any] = {}
    if isinstance(gates, dict):
        g3_obj = gates.get("G3_runtime_go_ratio")
        if isinstance(g3_obj, dict):
            g3 = g3_obj

    if g3.get("pass") is False:
        stress = max(stress, 0.25)
    else:
        observed = _floatish(g3.get("observed_ratio"))
        min_ratio = _floatish(g3.get("min_ratio"))
        if observed is not None and min_ratio is not None:
            if observed < min_ratio:
                stress = max(stress, 0.18)
            elif observed < (min_ratio + 0.05):
                # 게이트 통과이나 여유가 거의 없을 때 소량 가산
                stress = max(stress, 0.08)

    stress = _clamp(float(stress), 0.0, max_stress)

    if stress <= 1e-6:
        label = "off"
    else:
        label = "elevated"

    return stress, {
        "label": label,
        "path": str(artifact),
        "track": track,
        "commercial_ready": data.get("commercial_ready"),
        "max_stress": max_stress,
    }
