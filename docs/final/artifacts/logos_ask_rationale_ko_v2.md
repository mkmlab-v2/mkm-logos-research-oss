# 왜 “Logos Ask”는 ChatGPT-style UI가 아닌 “성경·텍스트 연구” 워크스페이스인가?

1. **사용자 기대** — 연구자는 텍스트·주석을 탐색하고, 인용-잠금(citation-lock)으로 신뢰성을 검증한다.
2. **스크립투리움 톤** — 크림 배경, 청록색 강조, 금색 포인트는 고전 서적을 연상시키며, 집중을 방해하지 않는다.
3. **시각-우선 흐름** — 첫 화면에 Composer + Quota strip가 배치돼 “첫 Aha”를 즉시 제공한다.
4. **S4 섹션 아코디언** — 5개의 핵심 인사이트를 카드-형식으로 단계적 공개, 스트리밍 시 강조 효과(테일 accent)로 진행 상황을 시각화한다.
5. **신뢰 스트립** — 인용-잠금이 가장 먼저 보이게 함으로써 “시간-검증된 지식”이라는 신뢰 레이어를 강조한다.

결과적으로 UI는 **읽기-쓰기-연구** 3-in-1 흐름을 지원하면서, 기존 React 컴포넌트·데이터 계약을 그대로 유지한다. 이는 “텍스트-중심 AI Q&A”라는 제품 차별성을 명확히 만든다.

**Merge:** Pack L-Ask v2 · `ASK_UI_REV=20260702e` · Cursor manual merge (Antigravity D3 diff partially superseded by Phase 0 accordion DOM).
