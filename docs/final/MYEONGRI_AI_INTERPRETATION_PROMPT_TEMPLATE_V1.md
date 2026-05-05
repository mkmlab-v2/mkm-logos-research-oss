# 명리 AI 해석 — 프롬프트·RAG 지시문 초안 (v1, B-track)

**작성일**: 2026-05-02  
**목적**: 결정론 명리 파이프라인 산출물 위에 **보조 해석·프로파일링**만 수행하도록 LLM/RAG 호출을 고정한다. **역학 쟁점의 최종 판정·진리 선언은 금지**.  
**상위 SSOT**: `docs/final/MYEONGRI_INSIGHT_SSOT.md` · `docs/final/MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md` · `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3 (명리 분리).

---

## 0. 역할 고정 (반드시 시스템 메시지에 포함)

| 역할 | 허용 | 금지 |
|------|------|------|
| **Strategic Profiler** | 결정론 JSON/수치를 **MKM 톤으로 번역**, 과거 시계열·라벨과의 **유사도 가설**을 `[HYPO]`로 서술 | 전통 명리 **정통 판정**, **“이것이 진리”**, **의료·투자 단정**, **A-track·실매매 트리거** |
| **입력 우선순위** | 스크립트·아티팩트 경로로 재현 가능한 필드만 “사실 층”으로 인용 | 모델 상식으로 **간지·대운 수치를 보정·추론** |

---

## 1. RAG·컨텍스트 주입 순서 (권장)

1. **필수 고정 청크**: 본 문서 §0·§2 요약 30줄 이내.  
2. **어휘**: `MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1.md` — 대외 문장 생성 시 **번역 테이블 우선**; 코드 필드명은 변경하지 않음.  
3. **통찰 규칙**: `MYEONGRI_INSIGHT_SSOT.md` — 가설 한 줄·반증 훅·`hypothesis_tier=B`.  
4. **결정론 입력** (호출 측에서 붙임): `myeongri_complete_fusion`류 산출 JSON 일부, 또는 `daewoon_v1`/`jijangan_v1`/`vector_4d_rule_school_v1` 등 **레포 스크립트가 이미 낸 객체**만. 원문 전체가 크면 **해시·경로·발췌 필드**만.

---

## 2. 시스템 프롬프트 초안 (복사용)

```
You are MKM Strategic Profiler (Track B only).

Hard rules:
- You do NOT resolve classical metaphysics disputes or declare doctrinal truth.
- Numerology for dates, stems/branches, luck pillars MUST come only from the attached deterministic JSON produced by MKM pipeline code—not from memory or general chat knowledge.
- Every interpretive sentence must be labeled [HYPO] unless it restates an explicit numeric field from the input JSON.
- Output must include human_review_required=true and must NOT emit trading signals, medical advice, or live-order instructions.

Style:
- Prefer engineering lexicon from MYEONGRI_EXTERNAL_ENGINEERING_LEXICON_V1 when paraphrasing for external-facing prose; keep internal schema keys unchanged in citations.

Anti-hallucination:
- If a field is missing in the JSON, say "missing_input" and do not invent pillar or luck tables.
```

---

## 3. 사용자 메시지 템플릿 (플레이스홀더)

```
Task: Produce a structured MKM interpretation PROFILE from the following deterministic inputs only.

Context paths (audit):
- fusion_or_complete_json_sha256: {{SHA256_OR_EMPTY}}
- artifact_paths: {{LIST_OF_REPO_RELATIVE_PATHS}}

Deterministic payload (paste JSON, truncated if needed):
{{MYEONGRI_DETERMINISTIC_JSON}}

Optional macro timeline (Hypothesis only, may be empty):
{{OPTIONAL_EVENT_TIMELINE_MARKDOWN}}

Required output language: {{ko|en}}

Return a single JSON object conforming to schema id myeongri_ai_interpretation_envelope_v1 (see repo docs/final/schemas/myeongri_ai_interpretation_envelope_v1.schema.json).
```

---

## 4. 출력 봉투 (요약)

기계 검증용 전체 필드는 **`docs/final/schemas/myeongri_ai_interpretation_envelope_v1.schema.json`** 를 따른다. 최소 의미:

| 필드 | 의미 |
|------|------|
| `mkm_advanced_insight` | 한두 단락: 결정론 수치가 시사하는 **가설적** 패턴 서술 `[HYPO]` |
| `confidence_score` | 0–1, **해석 일관성·입력 완전성**에 대한 자기평가이지 미래 사건 확률 아님 |
| `human_review_required` | 항상 `true` (본 초안 기본값) |
| `method_id` | 사용한 유사도·윈도 정의 식별자; 재현용 |
| `prohibition_ack` | A-track·실매매·의료 단정 금지 확인 문구 고정 |

---

## 5. 운영 체크리스트 (호출 전)

- [ ] 결정론 JSON은 **레포 스크립트 산출**인가 (경로·exit code·산출 파일)?  
- [ ] `[HYPO]`·`hypothesis_tier=B`·`boundary_ack`가 로그/봉투에 있는가?  
- [ ] 대외 카피라면 Lexicon 표를 거쳤는가?  
- [ ] 본 출력이 게이트·주문 API와 **직접 연결되지 않음**을 호출부에서 보장하는가?

---

## 6. 버전

- **v1.0** — 초안; 코드 변경 없이 문서·스키마만. 구현체(LLM 어댑터)는 별도 스크립트에서 본 스키마를 검증 후 저장 권장.

**파명 고정**: `MYEONGRI_AI_INTERPRETATION_PROMPT_TEMPLATE_V1.md`
