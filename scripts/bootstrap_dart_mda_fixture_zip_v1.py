#!/usr/bin/env python3
"""Bootstrap tests/fixtures/dart_mda_document_v1.zip (idempotent)."""

from __future__ import annotations

import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests/fixtures/dart_mda_document_v1.zip"

XML = """<?xml version="1.0" encoding="UTF-8"?>
<document>
  <title>사업보고서</title>
  <body>
    <section>이사의 경영진단 및 분석의견</section>
    <p>당사는 2024 회계연도에 연구개발비를 전년 동기 대비 12% 증가시켰으며, 이는 반도체 부문 선행 공정 투자 확대에 기인합니다. 메모리 사업부는 HBM3E 양산 ramp-up과 함께 재고 자산 회전일수가 전분기 대비 개선되었습니다.</p>
    <p>파운드리 사업부는 2나노급 공정 고객 tape-out이 증가하였으나, 유가증권시장 변동성 확대로 일부 고객의 capex 조정 가능성을 모니터링하고 있습니다. 당사는 환율 변동에 따른 원재료 조달 비용 상승 리스크를 재무적 파생상품으로 일부 헤지하고 있습니다.</p>
    <p>2025년 사업 전망에서 당사는 AI 서버 수요에 따른 고대역폭 메모리 수요 확대를 전제로 합니다.</p>
    <p>재무에 관한 사항</p>
    <p>이 섹션은 MD&amp;A 종료 마커 이후로 제외되어야 합니다.</p>
  </body>
</document>
"""


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(OUT, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("report.xml", XML.encode("utf-8"))
    print(OUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
