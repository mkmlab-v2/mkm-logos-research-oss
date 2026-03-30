from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, TypedDict
import json


class BiblicalSignal(TypedDict):
    id: str
    scope: str
    regime_templates: List[str]
    distance_to_centroid: float
    lambda_system: float
    pattern_ids: List[str]
    strength: float
    vector_p4_4d: Dict[str, float]
    meta: Dict[str, Any]


class MarketSignal(TypedDict):
    ts: datetime
    market_regime_label: str
    features: Dict[str, float]
    pattern_ids: List[str]
    strength: float
    meta: Dict[str, Any]


class FusionEvent(TypedDict):
    ts: datetime
    level: int
    biblical_refs: List[str]
    market_snapshot: MarketSignal
    action_recommendation: str
    rationale: Dict[str, str]


@dataclass
class FusionConfig:
    biblical_rules_path: Path
    market_rules_path: Path
    fusion_rules_path: Path


class FusionEngine:
    """
    성경 4D 신호와 시장 신호를 AND 규칙으로 결합하는 Fusion 엔진 스켈레톤.

    현재 버전은 JSON 룰을 로드하고, very basic한 매칭만 수행한다.
    트레이딩 루프에 본격 연결하기 전 단계의 설계/실험용이다.
    """

    def __init__(self, config: FusionConfig) -> None:
        self.config = config
        self._biblical_rules: Dict[str, Any] = {}
        self._market_rules: Dict[str, Any] = {}
        self._fusion_rules: Dict[str, Any] = {}
        self._load_rules()

    @staticmethod
    def _resolve_workspace_root() -> Path:
        # projects/bitcoin-trading/src/fusion/fusion_engine.py 기준으로 workspace 루트 계산
        current_file = Path(__file__).resolve()
        # fusion -> src -> bitcoin-trading -> projects -> workspace_root
        workspace_root = current_file.parent.parent.parent.parent.parent
        return workspace_root

    def _load_rules(self) -> None:
        def _load_json(path: Path) -> Dict[str, Any]:
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)

        self._biblical_rules = _load_json(self.config.biblical_rules_path)
        self._market_rules = _load_json(self.config.market_rules_path)
        self._fusion_rules = _load_json(self.config.fusion_rules_path)

    @classmethod
    def from_default_paths(cls) -> "FusionEngine":
        """
        workspace_root/projects/bitcoin-trading/config/fusion 아래의
        기본 룰 파일들을 사용하는 FusionEngine 생성자.
        """
        workspace_root = cls._resolve_workspace_root()
        base = workspace_root / "projects" / "bitcoin-trading" / "config" / "fusion"
        config = FusionConfig(
            biblical_rules_path=base / "biblical_signal_rules.json",
            market_rules_path=base / "market_signal_rules.json",
            fusion_rules_path=base / "fusion_rules.json",
        )
        return cls(config)

    # --- 신호 계산 스켈레톤: 이후 단계에서 구체 로직 보완 ---

    def compute_biblical_signals(
        self,
        regime_label: str,
        pool: List[BiblicalSignal],
        top_k: int = 5,
    ) -> List[BiblicalSignal]:
        """
        verse_4pipeline 등에서 미리 생성된 BiblicalSignal 풀에서
        현재 market_regime_label과 공명하는 상위 신호 몇 개를 선택한다.

        현재 버전은 regime_templates에 regime_label이 포함된 항목만 필터링하고,
        strength 기준으로 상위 top_k를 반환하는 간단한 구현이다.
        """
        if not pool:
            return []

        matched = [
            s
            for s in pool
            if regime_label in s.get("regime_templates", [])
        ]

        if not matched:
            # 레짐 직접 매칭이 없으면 전체 풀에서 상위 신호 반환 (실험용 fallback)
            matched = pool

        matched_sorted = sorted(matched, key=lambda s: s.get("strength", 0.0), reverse=True)
        return matched_sorted[:top_k]

    def compute_market_signal(
        self,
        raw_features: Dict[str, float],
        ts: datetime,
        regime_label: str,
    ) -> MarketSignal:
        """
        원시 피처에서 MarketSignal을 구성한다.
        현재 버전은 feature_thresholds를 참고해 간단한 패턴 ID와 strength만 부여한다.
        """
        feature_thresholds = self._market_rules.get("feature_thresholds", {})
        signal_templates = self._market_rules.get("signal_templates", [])

        # 매우 단순한 매칭: 첫 번째로 조건을 만족하는 템플릿 하나만 사용
        matched_id = ""
        strength = 0.0

        for tmpl in signal_templates:
            conditions = tmpl.get("conditions", {})
            ok = True
            for feature_name, band_key in conditions.items():
                band = feature_thresholds.get(feature_name, {}).get(band_key)
                if band is None:
                    ok = False
                    break
                value = raw_features.get(feature_name)
                if value is None:
                    ok = False
                    break
                min_v = band.get("min")
                max_v = band.get("max")
                if min_v is not None and value < min_v:
                    ok = False
                    break
                if max_v is not None and value > max_v:
                    ok = False
                    break
            if ok:
                matched_id = tmpl.get("id", "")
                strength = float(tmpl.get("strength", 0.0))
                break

        pattern_ids: List[str] = [matched_id] if matched_id else []

        market_signal: MarketSignal = {
            "ts": ts,
            "market_regime_label": regime_label,
            "features": raw_features,
            "pattern_ids": pattern_ids,
            "strength": strength,
            "meta": {},
        }
        return market_signal

    def fuse(
        self,
        market_signal: MarketSignal,
        biblical_signals: List[BiblicalSignal],
    ) -> FusionEvent:
        """
        사전에 정의된 fusion_rules.json을 기준으로
        성경 신호 + 시장 신호 AND 조건을 평가하여 FusionEvent를 생성한다.
        """
        levels = self._fusion_rules.get("levels", [])

        # 사용 중인 신호 ID 집합
        biblical_ids = {s["id"] for s in biblical_signals}
        market_ids = set(market_signal.get("pattern_ids", []))

        chosen_level = 0
        chosen_action = "none"
        now = market_signal["ts"]

        # 가장 높은 level부터 내려가며 첫 매칭을 채택
        for level_cfg in sorted(levels, key=lambda x: x.get("level", 0), reverse=True):
            required_biblical = set(level_cfg.get("biblical_signals_any", []))
            required_market = set(level_cfg.get("market_signals_any", []))
            min_strength = float(level_cfg.get("min_combined_strength", 0.0))

            has_biblical = bool(required_biblical & biblical_ids)
            has_market = bool(required_market & market_ids)

            if not (has_biblical and has_market):
                continue

            combined_strength = market_signal.get("strength", 0.0)
            # 가장 강한 성경 신호 하나만 더해 간단히 계산
            if biblical_signals:
                combined_strength += max(s.get("strength", 0.0) for s in biblical_signals)

            if combined_strength < min_strength:
                continue

            chosen_level = int(level_cfg.get("level", 0))
            chosen_action = level_cfg.get("action_recommendation", "none")
            break

        rationale = {
            "S": "성경 측 S(Spirit) 관점 요약은 이후 단계에서 주입합니다.",
            "L": "L(Logic) 관점에서는 룰 매칭 결과 level={} 이 도출되었습니다.".format(
                chosen_level
            ),
            "K": "K(Knowledge) 관점: verse_4pipeline 및 시장 피처를 결합한 실험적 Fusion 결과입니다.",
            "M": "M(Material) 관점: 현재 버전은 실제 포지션 강제 변경이 아닌 신호 모니터링용입니다.",
        }

        event: FusionEvent = {
            "ts": now,
            "level": chosen_level,
            "biblical_refs": [s["id"] for s in biblical_signals],
            "market_snapshot": market_signal,
            "action_recommendation": chosen_action,
            "rationale": rationale,
        }
        return event

