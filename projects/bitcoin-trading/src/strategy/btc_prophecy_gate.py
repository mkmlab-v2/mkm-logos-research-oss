#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BTC 예언 타임머신 검증 기반 레짐 게이트

최근 N개월 BTC 타임머신/월별 검증 결과를 바탕으로
자동매매 엔진의 "공격 모드 허용 여부"를 판단하는 보조 모듈.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
WORKSPACE_ROOT = PROJECT_ROOT.parent
VALIDATION_DIR = WORKSPACE_ROOT / "data" / "prophecy_validation"


@dataclass
class BTCProphecyGateResult:
    """BTC 예언 레짐 게이트 평가 결과."""

    allowed: bool
    match_ratio: float
    sample_count: int
    required_ratio: float
    evaluated_months: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "allowed": self.allowed,
            "match_ratio": self.match_ratio,
            "sample_count": self.sample_count,
            "required_ratio": self.required_ratio,
            "evaluated_months": self.evaluated_months,
        }


def _parse_year_month(name: str) -> Optional[str]:
    """
    파일명 또는 JSON의 year_month에서 YYYY-MM 문자열을 파싱.

    허용 형식:
    - 'monthly_validation_YYYYMM.json'
    - 'YYYY-MM'
    """
    if name.endswith(".json"):
        # monthly_validation_YYYYMM.json
        stem = Path(name).stem
        if stem.startswith("monthly_validation_") and len(stem) == len(
            "monthly_validation_YYYYMM"
        ):
            ym = stem.replace("monthly_validation_", "")
            try:
                dt = datetime.strptime(ym, "%Y%m")
                return dt.strftime("%Y-%m")
            except ValueError:
                return None
        return None

    # 이미 YYYY-MM 형식인 경우
    try:
        dt = datetime.strptime(name, "%Y-%m")
        return dt.strftime("%Y-%m")
    except ValueError:
        return None


def _load_monthly_validation(path: Path) -> Optional[Dict[str, Any]]:
    """단일 월별 검증 JSON을 로드."""
    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return None
        return data
    except Exception:
        return None


def evaluate_btc_prophecy_gate(
    months: int = 6,
    required_match_ratio: float = 0.6,
) -> BTCProphecyGateResult:
    """
    최근 N개월 BTC 타임머신/월별 검증 결과를 바탕으로
    공격 모드(레버리지·포지션 확대) 허용 여부를 평가.

    Args:
        months: 최근 몇 개 월에 대해 평가할지 (기본 6개월)
        required_match_ratio: 허용을 위해 필요한 최소 방향 일치 비율

    Returns:
        BTCProphecyGateResult: allowed 플래그와 상세 메트릭
    """
    if months <= 0:
        months = 1

    if not VALIDATION_DIR.exists():
        return BTCProphecyGateResult(
            allowed=False,
            match_ratio=0.0,
            sample_count=0,
            required_ratio=required_match_ratio,
            evaluated_months=[],
        )

    files = sorted(VALIDATION_DIR.glob("monthly_validation_*.json"))
    if not files:
        return BTCProphecyGateResult(
            allowed=False,
            match_ratio=0.0,
            sample_count=0,
            required_ratio=required_match_ratio,
            evaluated_months=[],
        )

    # year_month 기준으로 정렬
    records: List[Dict[str, Any]] = []
    for path in files:
        data = _load_monthly_validation(path)
        if not data:
            continue
        year_month = data.get("year_month") or _parse_year_month(path.name)
        if not isinstance(year_month, str):
            continue
        ym = _parse_year_month(year_month)
        if ym is None:
            continue
        data["year_month"] = ym
        records.append(data)

    if not records:
        return BTCProphecyGateResult(
            allowed=False,
            match_ratio=0.0,
            sample_count=0,
            required_ratio=required_match_ratio,
            evaluated_months=[],
        )

    records.sort(key=lambda d: d["year_month"])

    # 최근 N개월만 사용
    recent_records = records[-months:]

    evaluated_months: List[str] = []
    total_with_direction = 0
    direction_matches = 0

    for rec in recent_records:
        ym = rec.get("year_month")
        prediction = rec.get("prediction") or {}
        actual = rec.get("actual") or {}

        # BTC 예측/실제 값과 방향 일치 여부가 있는 달만 사용
        btc_match = rec.get("btc_direction_match")
        btc_pred_pct = prediction.get("btc_predicted_return_pct")
        btc_actual_pct = actual.get("crypto_return_pct")

        if btc_match is None:
            continue
        if btc_pred_pct is None or btc_actual_pct is None:
            continue

        total_with_direction += 1
        if bool(btc_match):
            direction_matches += 1
        if isinstance(ym, str):
            evaluated_months.append(ym)

    if total_with_direction == 0:
        return BTCProphecyGateResult(
            allowed=False,
            match_ratio=0.0,
            sample_count=0,
            required_ratio=required_match_ratio,
            evaluated_months=evaluated_months,
        )

    match_ratio = direction_matches / float(total_with_direction)
    allowed = match_ratio >= required_match_ratio

    return BTCProphecyGateResult(
        allowed=allowed,
        match_ratio=match_ratio,
        sample_count=total_with_direction,
        required_ratio=required_match_ratio,
        evaluated_months=evaluated_months,
    )


if __name__ == "__main__":
    # 간단한 수동 테스트용
    result = evaluate_btc_prophecy_gate()
    print(
        f"BTC 예언 게이트 결과: allowed={result.allowed}, "
        f"match_ratio={result.match_ratio:.3f} "
        f"({result.sample_count} samples, "
        f"required={result.required_ratio:.3f})"
    )
    if result.evaluated_months:
        print(f"평가 대상 월: {', '.join(result.evaluated_months)}")

