# Domain A HOLD outreach — outbound readiness (adversarial) v1.1

**상태:** `research_only` · `send_gate: HOLD` · **미발송** · 상용 DONE 아님  
**continuity:** `logos-domain-a-pii-2026-07-17`  
**판정시각(UTC):** 2026-07-17T10:25:00Z (must-fix 재채점)  
**대상 초안:** `docs/final/artifacts/mkm_domain_a_hold_pilot_outreach_draft_pack_v1_latest.md`

> 본 문서는 **발송 승인 문서가 아님**. 이전 팩의 「다음=발송 1건」은 **label≠reality / comfort-theater** 실패로 인정하고, must-fix 이후에도 **콜드는 보수**.

**Preflight (본 턴):** `Invoke-MkmHighDelegationPreflight_v1.ps1 -Scale M -Lane oracle` → exit 0 · `ready_for_auto=false` (browser soft / chat inject) · **로컬 문서·스크립트만 진행** · Track A/SEND 미주장.

---

## 1) Verdict (하나)

| 필드 | 값 |
|------|-----|
| **VERDICT** | **`DO_NOT_SEND`** (콜드 실회사) |
| `SEND_INTERNAL_ONLY` | 사내 초안 리뷰 OK |
| `SOFT_SEND_FRIEND` | **조건부 허용** — 친구에게 **녹화 또는 로컬 dogfood 팩**을 같이 줄 때만. 가짜 URL·“발송 1건” 재촉 금지. 기본은 여전히 보수. |
| `SEND_COLD_OK` | **아직 금지** |

**한 줄 이유:** must-fix로 **로컬 고객-실행 팩(A)+녹화 샷(B)+SOP intake 런북**은 생겼으나, **낯선 사람이 클릭할 공유 URL은 여전히 없음**. 콜드 메일은 vaporware 리스크가 남는다.

### `SEND_COLD_OK`가 가능해지는 조건 (명시)

1. 낯선 수신자가 **레포 클론 없이** 데모를 볼 수 있는 표면 (고품질 녹화 **+** 명확한 로컬 팩, 또는 지휘관 ACK된 private tunnel/sandbox URL — **존재하지 않는 VPS URL 창작 금지**)  
2. 최소 1회 **실고객 비식별 발췌**로 intake 표 회신 경험 (합성만이 아님)  
3. 아웃리치 카피 = PoC/맞춤 · §0 세일즈 수치 금지 준수  
4. 유료 파일럿 1-pager 비범위 유지  
5. readiness 재채점 + 지휘관 ACK  

---

## 2) Scorecard (0–10 · 증거 경로) — must-fix 후

| ID | 질문 | 이전 | **지금** | 증거 |
|----|------|------|----------|------|
| **A** | 엔지니어 babysitting 없이 오늘 데모가 되는가? | 3 | **6** | Customer-runnable pack: `py scripts/run_mkm_domain_a_customer_dogfood_pack_v0.py --smoke-only --expect-pass` exit0 · MD `mkm_domain_a_customer_dogfood_pack_v0_latest.md`. 여전히 **localhost** · 공개 VPS 없음. gap `product_path=partial` 유지. |
| **B** | 아웃리치가 gap 대비 과대광고인가? | 8 | **9** | v1.1: 「발송 1건」제거 · PoC 헤드라인 · sales ban list · fact-lock 재실행 기대. |
| **C** | 비MKM인이 15분 내 HOLD+audit를 볼 수 있는가? | 2 | **5** | 경로: (1) 로컬 팩 직접 실행 (2) 녹화 샷 리스트. **공개 클릭 URL은 없음** → 콜드엔 부족. |
| **D** | 파일럿 ask가 명확·비당황인가? | 7 | **8** | 유료 1-pager thin (기간·산출·환경·비범위 SIEM/법/PII). soft rewrite. |
| **E** | “우리 정책으로 보여줘” 당황 리스크 | 2→높을수록안전 | **5** | SOP intake stub exit0 · runbook 15–30분 · 표+audit 경로. **셀프서브 업로드 UX 없음** · 합성 fixture 우선. |
| **F** | AI법/보험 과대광고 | 8 | **8** | 금지 유지. |

**Metacog 4-check (재적용)**

1. **라벨≠실체:** 이전 「발송 1건」= comfort-theater → **수정함**. 남은 라벨 리스크: “파일럿” vs localhost stub.  
2. **정의 없는 수치:** 27/27 · false_pass=0 → **세일즈 금지 리스트 고정**.  
3. **불리한 지표 매장:** gap partial 유지 공개 · next≠발송.  
4. **재현:** dogfood smoke exit0 · sop intake exit0 · (fact-lock 본 턴 재실행).

---

## 3) Shame risks top 5 (잔여)

| # | 고객이 말하면 | 상태 |
|---|----------------|------|
| 1 | “링크 보내줘요” | **완화(부분):** 로컬팩/녹화는 있음 · **공개 URL은 여전히 없음** → 콜드에서 링크 약속하면 깨짐 |
| 2 | “SOP PDF 올리면?” | **완화:** intake 런북 15–30분 · 업로드 UX 없음 → “올리면 바로”는 여전히 거짓 |
| 3 | “SIEM에 넣자” | 변화 없음 · audit_ops partial |
| 4 | “PII 마스킹 포함?” | 변화 없음 · partial |
| 5 | “AI법 대응?” | 카피 벽 유지 · 구두 승격 주의 |

---

## 4) Must-fix before any outbound — 진행

| # | 항목 | 상태 |
|---|------|------|
| 1 | 공유 가능 데모 표면 | **PARTIAL** — A 로컬팩 + B 샷리스트 착륙 · 공개/터널 URL 없음(C는 Ask-Gate 문서만) |
| 2 | SOP 발췌 → stub 주입 런북 | **DONE (stub)** — `run_mkm_domain_a_sop_intake_stub_v0.py` exit0 · runbook |
| 3 | 아웃리치 PoC 재작성 | **DONE** — draft pack v1.1 |
| 4 | 유료 범위 1장 | **DONE (thin)** — outreach §4 |
| 5 | 세일즈 수치 금지 | **DONE** — outreach §0 |

콜드 `SEND_COLD_OK` / 실회사 발송 **재오픈 금지** until §1 조건.

---

## 5) Safe rewrite (현 초안 §2-A와 동일 계열)

PoC/맞춤 · 관심만 · 공개 URL 없음 — draft pack v1.1 §2-A 사용.

---

## 6) Repro evidence (must-fix 턴)

| 명령 | exit |
|------|------|
| `powershell -File scripts\Invoke-MkmHighDelegationPreflight_v1.ps1 -Scale M -Lane oracle` | **0** (`ready_for_auto=false`) |
| `py scripts/run_mkm_domain_a_customer_dogfood_pack_v0.py --smoke-only --expect-pass` | **0** |
| `py scripts/run_mkm_domain_a_sop_intake_stub_v0.py --expect-pass` | **0** (5/5) |
| `py scripts/check_external_facing_fact_lock_v1.py --target docs/final/artifacts/mkm_domain_a_hold_pilot_outreach_draft_pack_v1_latest.md` | **0** (violations=0) |

JSON: `reports/mkm_domain_a_hold_outreach_outbound_readiness_v1_latest.json`

---

## 7) Done cards (must-fix 턴)

| ID | user_visible_outcome | pass_evidence | non_scope | status |
|----|----------------------|---------------|-----------|--------|
| M1 | Customer-runnable dogfood pack (A) | dogfood pack MD+JSON · smoke exit0 | 공개 VPS URL | **DONE** |
| M2 | Recorded demo shot list (B) | `mkm_domain_a_hold_recorded_demo_shot_list_v0_latest.md` | Loom 실제 업로드 | **DONE** (script) |
| M3 | SOP intake stub+runbook | intake script exit0 · runbook · table | 실고객 PII · 업로드 UX | **DONE** (stub) |
| M4 | Outreach honesty + ban list + paid 1-pager | draft pack v1.1 | 실발송 | **DONE** |
| M5 | Readiness re-score · cold still HOLD | 본 MD §1–2 | SEND_COLD_OK | **DONE** |
| M6 | MISSION_LOG Oracle next≠발송 + checkpoint | MISSION_LOG · athena_checkpoint | — | **DONE** (본 턴) |
| M7 | Cold outbound / commercial DONE | — | **OPEN** | **OPEN** |

---

## 지휘관용 한 줄

**구멍은 메웠다(로컬팩·녹화각본·SOP 15–30분). 낯선 사람에게 오늘 메일? 아직 No — 클릭할 URL이 없다.**
