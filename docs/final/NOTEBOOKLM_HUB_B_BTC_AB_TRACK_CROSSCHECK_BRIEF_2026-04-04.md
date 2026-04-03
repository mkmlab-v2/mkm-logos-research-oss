# 금융 Hub B — BTC A/B 트랙 교차 검증 브리프 (Fact-Lock)

**문서 역할:** NotebookLM 금융 Hub B RAG 컨텍스트 보강. 내부 교차 검증(NotebookLM `cross_notebook_query` + 헌법 팩트) 결과의 SSOT 스냅샷.  
**유효일:** 2026-04-04  
**관련:** `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (Promotion Loop 등 §8), 금융 Hub B 노트북 ID `b79929a2-8742-42a8-a4d7-06523e12935d`

---

## Reasoning_Core (요약)

- **S [FACT]:** NotebookLM 교차 검증 결과, BTC 본선(A-track)에 OHLCV 피처 및 다중 온톨로지가 이미 적용되었다는 서술은 **확인되지 않음**. KOSPI 섀도우(B-track) 연구의 [HYPO]/[STRAT] 단계 교훈과 혼동하면 안 됨.
- **L:** KOSPI 연구 브리프의 교훈을 BTC 실매매 런타임으로 옮기려면 **Promotion Loop** 절차에 따른 **명시적 코드 반영**이 필요. 연구(B)와 본선(A)은 논리·운영상 분리(Air-gapped) 유지.
- **K [내부 규범]:** 통일장(TOE) **단일 방정식 비단정**, **NO_GO 기본값**. 헌법은 B-track 가설을 A-track 구현 팩트로 혼동하는 것을 금지.
- **M:** 헌법 문서 §8(Promotion Loop), 금융 Hub B 교차 질의 결과.
- **λ:** B-track 연구 과제를 A-track 구현 팩트처럼 묘사할 때의 **환각(Context 오염)** 리스크 — NotebookLM 팩트-락으로 차단.

---

## 1. 환각 차단 및 팩트 교정 (A/B 트랙 분리)

| 항목 | 상태 |
|------|------|
| OHLCV, intraday range/body ratio/volume surge/gap, 다중 하락 온톨로지(v18/v19류) | **B-track [HYPO]/연구 방향**으로 관리. BTC 실매매 코드 경로에 **[FACT]로 단정 금지**. |
| 듀얼 레짐 | 1차 실물(`regime_map` 등)과 2차 BTC 가설 레이어 **분리·격벽** — 단일 수식 합선 금지. |
| 단기 적중률(D5/D10 등) | 높아도 **S1_SHADOW 해제·LIVE 단독 근거로 사용 금지**. Chronos holdout 등 **Strict AND** 유지. |

---

## 2. 가드레일 [FACT] 정합 (교차 질의와 일치)

- **Strict AND 게이트:** 단기 hit만으로 shadow 해제 불가; 장기·신뢰 조건 AND.
- **PENDING_CLOSE:** API/데이터 획득 실패 시 무리한 추정·즉시 체결 금지, 관망·유보.

---

## 3. 운영 권고 [STRAT]

1. OHLCV·온톨로지 확장은 **연구 레인 검증 → Promotion 승인 후** A 반영.
2. 본선 서술·브리프·대외 설명에서 **구현 여부**는 호출 가능 코드·헌법 팩트표와만 대조.
3. 정기 감사: OPS 로그 수치와 문서 스냅샷 교차 검증은 별도 **Audit** 사이클.

---

## 4. 성공 판정 (이 소스 적재 후)

- NotebookLM 소스 목록에 본 문서 제목이 보이고, UI에서 본 브리프를 인용한 질의에 정상 응답.

---

*내부 전용. 대외 공유 시 표준 용어·비식별화 정책 준수.*
