# Domain A HOLD — recorded demo shot list v0 (Loom-ready)

**상태:** `research_only` · `send_gate: HOLD` · **가짜 공개 URL 없음**  
**용도:** Option **B** — 공유 가능한 **녹화 스크립트 + 샷 리스트**. 화면공유/Loom 전에 이 순서로 찍으면 됨.

> 고객에게 “링크”를 약속하지 말고, **녹화본** 또는 **로컬 dogfood 팩(A)** 을 준다.

---

## Prep (녹화 전 2분)

```text
py scripts/run_mkm_domain_a_customer_dogfood_pack_v0.py --smoke-only --expect-pass
py scripts/serve_policy_allowlist_hold_dogfood_ui_v0.py --port 8765 --open
```

브라우저: `http://127.0.0.1:8765/` · 주소창이 **127.0.0.1** 임을 한 번 말할 것(“로컬 PoC”).

---

## Shot list (총 ~6–7분)

| # | 시간 | 화면 | 말할 것 (정직) | 액션 |
|---|------|------|----------------|------|
| 1 | 0:00–0:30 | 터미널 + UI | “검색/법 인증 제품이 아니라 **정책 게이트 PoC**입니다.” | — |
| 2 | 0:30–1:30 | UI | “허용이면 PASS.” | 질의 `pol.read_employee_handbook` → PASS |
| 3 | 1:30–3:00 | UI | “모르면 HOLD + 이유코드.” | `wire transfer customer funds` → HOLD/OOV_HOLD |
| 4 | 3:00–4:00 | `/api/audit?n=20` | “감사 한 줄이 JSON으로 남습니다. SIEM 연동 아님.” | 브라우저로 audit API |
| 5 | 4:00–5:30 | 터미널 | “합성 SOP/약관 near-real도 CLI로 재현.” | `py scripts/run_mkm_domain_a_synthetic_sop_yagwan_demo_v0.py --expect-pass` |
| 6 | 5:30–6:30 | 표 MD (선택) | “고객 발췌가 오면 이 intake로 15–30분 맞춤.” | `mkm_domain_a_sop_intake_pass_hold_table_v0_latest.md` 열기 |
| 7 | 6:30–7:00 | 닫기 | “공개 SaaS URL 없음. 다음=유료 파일럿 범위 합의. 법완료 주장 없음.” | 정지 |

---

## Screenshot pack (최소 4장 · 파일명 제안)

저장 위치 권장: `reports/domain_a_demo_shots/` (로컬; 실고객 화면 커밋 금지)

1. `01_ui_pass.png` — PASS 결과
2. `02_ui_hold.png` — HOLD/OOV_HOLD
3. `03_audit_api.png` — audit JSON
4. `04_cli_synthetic_sop.png` — CLI exit0 요약

---

## 고객에게 보낼 때 문장

> “지금은 **로컬 PoC**입니다. 공유용으로 **짧은 녹화**와 **귀사 비식별 SOP 발췌 → PASS/HOLD 표** 절차를 준비했습니다. 공개 제품 URL은 아직 없습니다.”

---



## Auto capture status (v0)

- **auto capture DONE** — `docs/final/artifacts/mkm_domain_a_hold_auto_demo_capture_v0_latest.md` · shots under `reports/domain_a_demo_shots/`
- Loom cloud upload: **still human** (계정 로그인 필요)
- Voiceover: **still human**
- Re-run: `py scripts/run_mkm_domain_a_hold_auto_demo_capture_v0.py`

## Walls

- 녹화 ≠ 라이브 멀티유저 SaaS
- 샷에 실PII / 실회사 내부화면 넣지 말 것
- 27/27 · false_pass=0 헤드라인 금지
