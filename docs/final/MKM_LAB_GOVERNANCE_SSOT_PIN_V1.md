# MKM LAB Governance SSOT Pin v1

**Status:** `PINNED` · structural governance only  
**Commander ACK:** `COMMANDER_MKM_GOVERNANCE_SSOT_PIN_ACK`  
**Canonical machine artifact:** `docs/final/artifacts/mkm_lab_governance_ssot_pin_v1_latest.json`  
**Write receipt:** `docs/final/artifacts/mkm_lab_governance_ssot_pin_write_receipt_v1_latest.json`  
**research_only:** true · **send_gate:** HOLD  

## Purpose

Cursor / ChatGPT / coding agents / validators / product lanes가 **동일한 사실·권한·evidence ceiling 규칙**을 읽도록 하는 1인 운영(solo-ops) 거버넌스 헌법 핀.

## Success ceiling (이 핀의 PASS 의미)

- **PASS =** 거버넌스 규칙이 구조적으로 핀됨 (path + version + hash + receipt).
- **PASS ≠** Evidence Ledger 구현 · semantic reliability · product readiness · autonomous ops 승인.

## 1. Evidence hierarchy (높은 쪽이 이김)

1. `CURRENT_SOURCE` / `AUTHORITATIVE_ARTIFACT`
2. `SEAL` / `RECEIPT`
3. `CURRENT_STATE`
4. `WORKER_REPORT`
5. `CHAT` / `MEMORY`
6. `INFERENCE`

## 2. Epistemic states (허용 라벨)

`FACT` · `SUPPORTED` · `INFERENCE` · `HYPOTHESIS` · `UNKNOWN` · `NOT_ESTABLISHED` · `NOT_ADJUDICATED` · `FAIL`

## 3. Hard distinctions (합선 금지)

| 금지 합선 | 의미 |
|-----------|------|
| worker claim ≠ evidence | 워커/에이전트 주장만으로 증거가 되지 않음 |
| exit 0 ≠ semantic success | 프로세스 성공 ≠ 의미/품질 성공 |
| implementation PASS ≠ effectiveness | 구현 통과 ≠ 효과 입증 |
| harness PASS ≠ PRODUCT_DONE | 하네스 통과 ≠ 제품 완료 |
| candidate ≠ authorization | 후보 ≠ 실행 권한 |
| HOLD ≠ PASS | 보류는 통과가 아님 |

## 4. Freshness lock

`result → patch → rerun` 은 **독립 fresh evidence가 아님**.  
동일 set에 대한 patch-after-fail 재실행은 DEV/repair 레인으로만 기록한다. sealed fresh 결과를 덮어쓰지 않는다.

## 5. Builder / Validator separation

Builder self-report alone **cannot seal semantic success**.  
Semantic seal은 validator/independent check + (해당 시) Commander adjudication가 필요하다.

## 6. Human / Commander gates

다음 행위는 **명시적 Commander 승인**이 필요하다.

- `SEND`
- `DEPLOY`
- `LIVE_PROMOTION`
- destructive action (삭제·권한확대·결제·DNS write 등 고영향 변경)

기본값: `SEND_GATE: HOLD`

**Delegated execution tiers (operational fence — does not replace this pin):**  
`docs/final/MKM_DELEGATED_EXECUTION_POLICY_V1.md` · machine `docs/final/artifacts/mkm_delegated_execution_policy_v1_latest.json`  
GREEN = preauthorized internal reversible work may auto-chain inside authorized scope · YELLOW = prepare OK, execute needs Commander · RED = explicit Commander only. First semantic/fresh FAIL → seal + STOP (no patch-rerun as fresh).

## 7. Lane separation (증거·권한 자동 합선 금지)

다음 레인은 evidence와 authorization을 **자동으로 합치지 않는다**.

- Logos research (`logos.jema-ai.com` KEEP)
- Bible consumer adapter (`mutda.ai/bible` Beta)
- MUTDA News (`mutda.ai/news`)
- future product lanes

Surface role pin companion: `docs/final/artifacts/mkm_mutda_logos_surface_role_pin_v1_latest.json`

## 8. Solo-ops rule

AI agents may **prepare / build / check**.  
No agent may promote its own output **above its evidence ceiling**.

## Related (does not override this pin)

- Implementation fact paths: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`
- Commander Operator design candidate (NOT this pin): `docs/final/MKM_COMMANDER_OPERATOR_CONSTITUTION_V0_1.md`
- Send vocabulary: `docs/final/artifacts/mkm_send_gate_vocabulary_v1_latest.json`
- Delegated execution operational policy: `docs/final/MKM_DELEGATED_EXECUTION_POLICY_V1.md` (GREEN/YELLOW/RED · AUTO_NEXT-within-scope)

## Queued (NOT started by this pin)

- Evidence Ledger v0
- Agent role wiring
- Deterministic gate automation beyond existing scripts
- Product-specific validator binding

## Revision

| date_utc | change | ack |
|----------|--------|-----|
| 2026-09-03T17:39:49Z | v1.0.0 structural pin | COMMANDER_MKM_GOVERNANCE_SSOT_PIN_ACK |
| 2026-09-07T19:20:00Z | pointer to Delegated Execution Policy v1 (tiers; no pin rewrite) | MKM_DELEGATED_EXECUTION_GOVERNANCE_V1_ACK |
