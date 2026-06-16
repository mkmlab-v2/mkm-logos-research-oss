---
schema: mkm_multi_axis_promotion_gate_policy_v1
version: v1
status: frozen_policy
research_only: true
send_gate: HOLD
ready_for_external_send: false
track_a_active_untouched: true
promotion_cascade_forbidden: true
policy_pointers:
  - docs/final/COMPRESSION_SLA_POLICY_V1.md
  - docs/final/COMPRESSION_12M_LEARNINGS_AND_TRACKB_PLAYBOOK_2026-04-08.md
  - docs/final/artifacts/compression_sku_separation_brief_v1_latest.json
  - docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md
  - .cursor/rules/tracka-raw-gate-guard-v1.mdc
  - .cursor/rules/raw-repair-dual-reporting-v1.mdc
attest_script: scripts/validate_mkm_multi_axis_promotion_gate_policy_v1.py
generated_at_utc: 2026-06-16
---

# MKM 4축 독립 승격 가드레일 매트릭스 v1

**목적:** B-track `[HYPO]` PoC·데모 통과가 Track A 본선·MASK Tier A·대외 송출·COORD 상용 주장으로 **연쇄 합선(cascade)** 되는 거버넌스 오독을 원천 봉쇄한다.

**격벽 원칙:** `FAIL-COMP-004` — 한 축의 게이트 개방이 타 축의 `ACTIVE swap`·`ready_for_external_send: true`·Track A KPI 헤드라인을 **자동 트리거하지 않는다**.

---

## 0. 전역 포스처 (고정)

| 태그 | 값 |
|------|-----|
| 기본 레일 | B-track `[HYPO]` · `research_only` |
| `send_gate` | **HOLD** (명시적 법무·지휘관 해제 전) |
| 연쇄 승격 | **금지** (`promotion_cascade_forbidden: true`) |

**rib55 위상:** rib55·COORD passive audit·pytest exit 0 = **축 1 내부 검증** + **축 2 기하학 PoC** 증거일 뿐. **축 3·4 대체 증거 아님.**

---

## 1. 4축 독립 통제 평면

| 축 ID | 승격 타깃 | 현재 위치 | 통과 앵커 (결선 요건) | 합선 방화벽 |
|-------|-----------|-----------|----------------------|-------------|
| **AX-1** | rib55 대외 송출 (교육 자산) | `[HYPO]` | Human adjudication checklist 6항 · CC-BY-SA attribution · **`HOLD_LEGAL_REVIEW` 해제** · 명시적 송출 결정 | `apply_rib55_overlay_adjudication_v1.py`는 **`send_gate` HOLD 유지** · `ready_for_external_send` 자동 true **금지** |
| **AX-2** | SKU-COORD 제품/SDK | Blueprint | bilateral ground truth (base SHA + coord_spec) · edge/on-prem SDK **실물** · signoff envelope | MASK PoC % · Track A 47.5% · 「COORD SDK 완전 출시」 헤드라인 **금지** |
| **AX-2-PoC** | COORD 기하학 PoC (연구) | **증거 수립됨** | wire example · v2 stub roundtrip · multi-entry bench · passive audit exit 0 | **≠ AX-2 제품화** · **≠ AX-3 Track A** |
| **AX-3** | Track A 압축 본선 (Core API) | 격리 | COMPRESSION §9 전체 · `alignment_pass_rate(raw)` 통과 · named scope PR · CONSTITUTION 갱신 · 지휘관 승인 | `repair_v2` only uplift **금지** · rib55/COORD **대체 불가** |
| **AX-4** | SKU-MASK (Deep Pack) | Tier A 분리 | hybrid router spike ~86.7% (corpus-scoped) · tri-vertical checklist · 별도 signoff | COORD·rib55 지표와 **독립 체인** |

**규칙:** AX-2-PoC 통과 ⊄ AX-2 제품화 ⊄ AX-3 ⊄ AX-4 ⊄ AX-1. 각 축은 **별도 evidence pack** 만으로 Attest한다.

---

## 2. 연쇄 금지 선언 (기계·에이전트용)

다음 추론은 **항상 거짓**으로 취급한다:

1. 「rib55 adjudication 통과 → 본선 압축 API OPEN」
2. 「COORD wire ~156 tok → Track A 47% 달성」
3. 「MASK Tier A 86.7% → COORD SDK 출시」
4. 「repair_v2 alignment pass → raw gate 충족」
5. 「B-track pytest green → `send_gate` 자동 해제」

---

## 3. 증거·재현 (Fact-Lock)

| 산출 | 경로 |
|------|------|
| 본 정책 MD | `docs/final/artifacts/mkm_multi_axis_promotion_gate_policy_v1.md` |
| 기계 Attest JSON | `docs/final/artifacts/mkm_multi_axis_promotion_gate_policy_v1_latest.json` |
| 검증 | `py scripts/validate_mkm_multi_axis_promotion_gate_policy_v1.py` **exit 0** |
| COORD PoC 체인 | `py scripts/run_rib55_coord_passive_audit_v1.py --skip-pytest` **exit 0** |

---

## 4. 승격 시 필수 human gate

| 축 | Human |
|----|-------|
| AX-1 | 법무 + 지휘관 송출 결정 |
| AX-2 | 제품/아키텍처 signoff + 배포 모드 선택 |
| AX-3 | 지휘관 PR + §9 체크리스트 서명 |
| AX-4 | MASK/deep-pack signoff envelope |

**자동화·adjudication·CI만으로는 AX-1~4 중 어느 것도 완료로 기록하지 않는다** (AX-2-PoC 제외).

---

**Revision:** 2026-06-16 — v1 frozen · 4-axis cascade guard · CONSTITUTION §1.2 pointer.
