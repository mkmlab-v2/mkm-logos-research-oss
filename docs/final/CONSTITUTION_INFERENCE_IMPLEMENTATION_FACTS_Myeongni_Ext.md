# CONSTITUTION — 명리·이제마 B 확장 (경계만)

**작성일**: 2026-03-29  
**주 문서 (SSOT)**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`  
**목적**: B 트랙(만세력·사주 NotebookLM) 전용 **추론 경계**를 짧게 고정한다. 본문 **중복** 없음.

---

## 1. 적용 범위

- **포함**: 이제마 **B** 노트북 소스, `MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` 메타, B용 코퍼스 (`data/corpus/ijeoma/**`).  
- **제외**: 한의 라벨 코호트 **A**, 204 OOF 본선, 자동 매매·실전 트리거 (별도 헌법·팩트).

---

## 2. SSOT 포인터 (본 문서 § 참조)

| 주제 | 본 FACTS |
|------|----------|
| 구현·경로·금지 | §3, §6, §7 |
| NotebookLM·노트 ID | §8 |
| 스키마 파일 | `docs/final/MYEONGNI_FUSION_DECISION_JSON_SCHEMA.json` |

---

## 3. B 전용 규칙 (한 줄씩)

1. **추론만 존재하고 구현 경로가 없으면** 본선 자동화·OOF와 **연결하지 않는다** (§7).  
2. **원전 청크**는 인용 위조 없이; 스캐폴드·가설은 문서에 명시 (`jeokcheonsu_core_logic_chunk.md`).  
3. **A/B**: 코호트 A 원전·Proxy **B** 말뭉치 **혼선 금지** — `KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md`.  
4. NotebookLM 소스 목록은 `docs/NotebookLM_sources_manifest.md` **이제마_B_Track**과 동기화.

---

**상태**: Final (경계 문서) · 매니페스트에 경로 등록 시 **Pending Ingest** 가능
