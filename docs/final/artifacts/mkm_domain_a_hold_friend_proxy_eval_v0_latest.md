# Domain A HOLD — friend-proxy eval v0 (external LLM)

**상태:** `research_only` · `send_gate: HOLD` · **미발송**  
**생성:** 2026-07-17T13:10:00Z (approx)  
**continuity:** `logos-domain-a-pii-2026-07-17`  
**JSON:** `reports/mkm_domain_a_hold_friend_proxy_eval_v0_latest.json`

> **정직 라벨:** 실제 인간 친구가 데모를 본 것이 아님.  
> **외부 LLM** (`gemini-2.5-flash` via `scripts/ask_gemini_v1.py`)이 PNG 설명·MD 브리프를 보고 답함.  
> **mp4는 시청 불가** — 판정은 PNG 4장 + gallery/outreach/readiness MD만.

---

## 1) Source

| 필드 | 값 |
|------|-----|
| `source` | `gemini-2.5-flash` (Google AI Studio · `ask_gemini_v1.py`) |
| `source_class` | `external_llm` |
| `local_proxy_after_api_fail` | false |
| `video_watched` | **false** (agent/LLM cannot play mp4; PNG+MD only) |
| `human_friend_watched` | **false** |
| `prompt_path` | `reports/domain_a_demo_shots/_friend_eval_prompt_v0.txt` |
| `raw_response_path` | `reports/domain_a_demo_shots/_friend_eval_gemini_raw_v0.txt` |

**시도 순서:** Gemini API 키 존재 → 호출 **성공(exit 0)**. NotebookLM은 활성 노트북이 금산 스마트팜이라 Domain A와 무관 → 스킵. OpenRouter 미사용(Gemini 성공).

---

## 2) Materials shown (to the proxy)

1. Gallery MD: `mkm_domain_a_hold_auto_demo_capture_v0_latest.md`
2. PNGs: `01_ui_pass` · `02_ui_hold` · `03_audit_api` · `04_cli_synthetic_sop`
3. Outreach honesty: draft pack v1.1 soft
4. Readiness: outbound readiness v1.1 (`DO_NOT_SEND` cold · soft friend conditional)
5. mp4 present locally but **not watched**

---

## 3) Verdict (friend soft / cold)

| Audience | Verdict | 한 줄 |
|----------|---------|--------|
| **Friend soft** | **PARTIAL / 보수** | 외부 LLM: 「친구에게 그냥 보내기 = 아니오」. 옆에서 설명+녹화/로컬팩이면 관심 타진만 가능. |
| **Cold outbound** | **DO_NOT_SEND** 유지 | 외부 LLM: 「절대 아니오」. readiness와 일치. |

`cmd-friend-soft` → **PARTIAL** (proxy done · 실친구 시청/ACK 아님).

---

## 4) External quotes (Gemini · KR)

### Q1 — 10초 제품
> AI나 자동화 시스템이 뭔가 하려 할 때, 미리 정해둔 허용 목록에 없으면 일단 **HOLD(멈춤)** 시키고 왜 멈췄는지 기록하는 보안/정책 게이트.

### Q2 — 사고/모름/허접
> **아직 허접하다.** … 그냥 내부 개발 툴이야. 고객한테 보여줄 만한 수준은 전혀 아님.

### Q3 — 창피한 점
> `C:\workspace\reports` 이런 경로 … 개발자 노트북에서 돌리는 거구나  
> 너무 개발자용 UI …  
> 유료 파일럿은커녕 PoC도 민망한 수준인데 저런 문구가 오히려 비웃음

### Q4 — 친구에게 보내도?
> **아니오.** 같이 앉아서 옆에서 설명해줘야 …

### Q5 — cold mail?
> **절대 아니오.** … 보냈다간 회사 이미지 망칠 수도

### Q6 — 고칠 것 3개 (우선순위)
1. UI/UX 다듬기 (내부 툴 느낌 제거)
2. 클라우드/접속 가능 데모 환경 (`127.0.0.1` 탈피)
3. 비엔지니어용 비즈니스 가치 설명

### Compliance advisor (trouble claims)
> 성숙도 과장 · 운영급 보안처럼 읽히는 주장 · `3/3`·`false_pass=0` 세일즈 수치 · 「유료 파일럿」과 NOT paid-pilot/DO_NOT_SEND 상충 · 합성 PII를 실고객 PII 처리 능력처럼 암시

---

## 5) Market context `[HYPO]` (web · not product proof)

Enterprise AI 쪽은 **런타임 governance / deterministic admission gate / policy-as-code + audit** 서사가 늘고 있음(예: runtime governance 글, Gateia·trust-gate류 deterministic verifier).  
→ Domain A 「모르면 멈춤 + audit」 **문제 정의는 시장과 결이 맞을 수 있음** `[HYPO]`.  
→ 그러나 본 데모 표면(localhost·개발자 UI·공개 URL 없음)은 **그 카테고리의 상용 제품처럼 보이지 않음** — 외부 Gemini 판정과 동일.

---

## 6) Commander 한 줄 (쉬운 말)

**외부 Gemini가 본 결론:** “아이디어는 알겠는데, 지금은 개발자용 숙제 수준. 친구에게 파일만 던지지 말고, 낯선 회사 메일은 절대 보내지 마.”  
콜드는 계속 **DO_NOT_SEND**. 친구 soft는 **PARTIAL** — 옆에 앉아 설명하거나 녹화+로컬팩을 같이 줄 때만 재검토.

---

## 7) Walls

- external LLM ≠ 실친구 시청
- PNG/MD 기반 · mp4 미시청
- 이 문서 ≠ SEND 승인
- market `[HYPO]` ≠ Track A / commercial DONE
