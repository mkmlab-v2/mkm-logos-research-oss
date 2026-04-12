# MKMLIFE — 뉴스 토픽 · 질문 스타터 번들 (NotebookLM B 궤적)

**역할:** Creative-Lock · 브리핑·RAG 보강. **A(Fact-Lock)·본선 OOF·실매매·압축 엔진과 자동 합선 금지.**  
**갱신:** 2026-04-12  
**관련:** `docs/final/NOTEBOOKLM_HUB_B_BTC_AB_TRACK_CROSSCHECK_BRIEF_2026-04-04.md`(A/B 격벽) · `docs/final/NOTEBOOKLM_GENERAL_PROPHECY_VPS_GIT_FORESIGHT_BUNDLE_2026-04-11.md`(층 A/B/C·전망 방법) · `projects/mkm/mkm-life`(공개 랜딩 톤: 정보·대화 보조)

---

## 1) 한 줄 요지

**“오늘의 헤드라인”을 사용자가 One Question으로 넘기기 쉽게** 하기 위해, 뉴스 토픽마다 **질문 각도(스타터)만** 제안한다.  
답의 정답·투자·안보 예측을 **서비스가 보장하지 않는다.** 스타터는 **참고용 아이디어**이며, 편향을 없앤다는 **마케팅 단정은 쓰지 않는다.** 대신 **출처·갱신 시각·레일(B)** 을 명시한다.

---

## 2) 격벽 (레포 정신과 동일)

| 금지 | 이유 |
|------|------|
| B 궤적 산출물을 **압축 KPI·레짐·실매매 게이트**에 직접 연결 | `CONSTITUTION` · Hub B 브리프와 동일 |
| **종목·매수·매도·수익률**을 스타터 문장에 **단정** | 투자 자문·미등록 리스크 |
| **전쟁·재난 발생 여부**를 서비스가 **예언**하는 톤 | 안보·민감 콘텐츠·오해 |
| NotebookLM 요약을 **구현 SSOT**로 단정 | 매니페스트 A/B 정의와 동일 — **레포·스크립트·artifacts**가 팩트 |

---

## 3) 층 나누기 (일반예언 번들과 정렬)

| 층 | 내용 | MKMLIFE 뉴스 스타터에 대응 |
|----|------|---------------------------|
| **A — 사실·출처** | 헤드라인·날짜·링크(가능하면 복수 출처) | 토픽 카드 상단: `sources[]`, `as_of_utc` |
| **B — 각도·질문 분해** | “무엇을 확인하면 좋은가” (시나리오·불확실성) | `suggested_questions[]` — **질문만**, 답 없음 |
| **C — 해석·가치판단** | 사용자·One Question 채팅에서만; **스타터에 성경·명리·단일 TOE 혼입 금지** | 제품 카피·mkmlife 세속 포지션 유지 |

---

## 4) JSON 스키마 초안 (`news_question_starter_v1`)

구현 전 스냅샷·정적 파일·배치 출력에 공통으로 쓸 수 있는 최소 필드.

```json
{
  "schema": "news_question_starter_v1",
  "rail": "B",
  "generated_at_utc": "2026-04-12T00:00:00Z",
  "topic_id": "example_topic_001",
  "headline_summary": "한 줄 요약 (사실 단정 최소화)",
  "sources": [
    { "label": "출처명", "url": "https://example.com/article" }
  ],
  "suggested_questions": [
    "이 사안에서 공식 입장·후속 일정을 확인하려면 무엇을 보면 좋을까?",
    "시장 변동성 측면에서 ‘원인 vs 상관’을 구분하려면 어떤 지표를 함께 볼 수 있을까?"
  ],
  "disclaimer": "투자·법률·안보·의료 조언이 아닙니다. 질문은 아이디어일 뿐입니다."
}
```

- **민감 토픽**(지정학·재난 등)은 `suggested_questions`를 **확인 질문·정보 출처** 중심으로만 두고, **특정 국가·종목을 단정하는 문장**은 넣지 않는다.

---

## 5) NotebookLM · Vault 작업 순서

1. **레포 SSOT:** 본 파일을 `docs/NotebookLM_sources_manifest.md` B 궤적 표에 등록한다.  
2. **Vault 미러:** `powershell -NoProfile -ExecutionPolicy Bypass -File scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1`  
3. **NotebookLM:** 작전지휘부 또는 MKMLIFE 전용 허브 노트북에 `source_add`(파일 경로 = 본 MD). MCP 미주입 시 UI에서 동일 파일 업로드.  
4. **교차 검토:** `cross_notebook_query` 등으로 **“스타터가 투자 조언으로 읽히는가?”** 한 번 필터링 (Hub B BTC 브리프와 같은 감사 습관).

---

## 6) 제품(mkmlife) 반영 시 권장 UX

- 랜딩/앱: **「오늘의 토픽 · 질문 아이디어(베타)」** + **B 레일** + **면책** 고정.  
- 데이터: 앱은 **레포·CDN·정적 JSON**만 읽고, **실시간 생성형을 본선 압축·거래와 같은 파이프라인에 합치지 않는다.**

---

## 7) 다음 구현(코드) — 선택

| 단계 | 내용 |
|------|------|
| 1 | `docs/final/artifacts/news_question_starter_sample_v1.json` — 스키마 샘플 1건(예시 URL; 실제 운영 시 교체) |
| 2 | `projects/mkm/mkm-life`에 읽기 전용 섹션 컴포넌트 (JSON fetch 또는 빌드 시 정적 import) |
| 3 | 야간 배치가 JSON만 갱신 — **GO 전 지휘관 승인** |

---

*내부 전용 브리핑. 대외·상용 문구는 법무·면책 정책과 별도 정합.*
