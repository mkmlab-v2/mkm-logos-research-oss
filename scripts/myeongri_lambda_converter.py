# -*- coding: utf-8 -*-
"""명리 λ 스칼라 변환 (MyeongriController 연동용).

현재 컨트롤러는 인스턴스만 보관하며 별도 호출은 하지 않는다.
필요 시 4D 벡터에서 λ 단일값을 도출하는 훅으로 확장한다.
"""

from typing import Any, Dict


class MyeongriLambdaConverter:
    def __init__(self) -> None:
        pass

    def scalar_from_4d(self, vector_4d: Dict[str, Any]) -> float:
        """4D 합계 편차로 단순 λ 근사 (기본 0.25 부근)."""
        s = sum(float(vector_4d.get(k, 0.25)) for k in ("S", "L", "K", "M"))
        return float(min(0.5, max(0.0, abs(s - 1.0))))
