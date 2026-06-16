---
schema: anatomy_image_hallucination_control_protocol_hypo_v1
labels: [HYPO, research_only, publish_allowed=false]
send_gate: HOLD
ready_for_external_send: false
economic_edge_claim_allowed: false
policy_pointers:
  - docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md
  - reports/han_voice_rib55_vault_index_v1_latest.md
reference_only:
  - "G:/공유 드라이브/MKM_DATA_VAULT/notebooklm_sources/일반예언/9번늑골_이미지수집_크롤링_팩트체크_2026-02-26.md"
evidence_paths:
  - docs/final/artifacts/rib55_angle_overlay_manifest_v1.json
---

# [HYPO] 해부학 도판 환각 제어 및 라이선스 컴플라이언스 프로토콜 v1

- **상태:** `[HYPO] · research_only`
- **레일:** 가설 1 = Track A 인접 ops · 가설 2 = Track B 격리
- **통제:** `SEND_GATE: HOLD` · `ready_for_external_send: false` · `economic_edge_claim_allowed: false`
- **CONSTITUTION:** 본문 편입 **유예** (스크립트·pytest·exit 0 전)
- **NL 참고:** `01 · 지휘·운영` 노트북 정합(참고만; 레포 SSOT 단독 근거 아님)

---

## §1. 목적 및 배경

한의 음성학 교재 및 B2B 연수 자료에 탑재될 해부학 도판(흉곽, 9번 늑골, 횡격막 구조 등) 제작 시, 생성 AI의 구조적 환각(Hallucination)을 제어하고 저작권·라이선스 위험을 차단하기 위한 **통제 평면 정책**이다.

**핵심 원칙:** 픽셀 생성은 확률적이고, 코드 기반 합성은 결정론적이다. 의학 출판 수준의 해부 무결성은 생성 AI 단독으로 기계 보장할 수 없다.

---

## §2. 핵심 가설 및 아키텍처 배관

### 가설 1. 정적 원본 기반 좌표 오버레이 배관 (우선순위 1 · Track A 인접)

- **개념:** AI에게 이미지 창작을 전면 방임하지 않고, 라이선스가 입증된 정적 원본 위에 기하학적 각도선·화살표·캡션 메타데이터를 시스템 코드로 합성한다.
- **물리 명세:** `anatomy_overlay_coord_v1` 규격 · 매니페스트 `docs/final/artifacts/rib55_angle_overlay_manifest_v1.json`
- **장점:** 오버레이 기하학 레이어는 **결정론적**이며, 생성 AI 대비 **구조적 환각 경로를 차단**한다. GPU 불필요.
- **한계:** Commons 원본 해부 오류·좌표 수동 지정·투영 스케일 오차는 **별도 human adjudication** 대상이다. 「미세 드리프트 0」 주장 금지.

**압축 SKU 격벽:** 본 배관은 `SKU-COORD` / `SKU-MASK`(압축 메타와이어)와 **명칭·축 분리** — `anatomy_overlay_coord_v1`만 사용.

### 가설 2. 벡터 가이드 기반 질감 샌드박스 (우선순위 2 · Track B 격리)

- **개념:** 구조 골격은 검증된 SVG 벡터로 1층 고정(Lock); 생성 AI는 2층에서 표면 질감·명암만 렌더링.
- **물리 명세:** `anatomy_texture_sandbox_v1` — 마스크 경계 침범(Mask Bleed)·구조 왜곡 감시.
- **장점:** 시각 품질 보조 가능.
- **한계:** SVG 출처 검증·블리드 리스크 · **출판 본선은 가설 1 파일럿 통과 후**만 검토.

---

## §3. 엄격 통제 가드레일 (격벽 원칙 준용)

압축 `FAIL-COMP-004` 계열과 동일한 **축 분리·헤드라인 합선 금지** 원칙을 이미지 레인에 준용한다 (압축 KPI 축과 **1:1 동일시 금지**).

| 태그 | 규칙 |
|------|------|
| **[DATA]** | 구글 등 출처 불명 이미지 무단 수집·AI 재가공 **금지**. Wikimedia Commons · PMC/Open Access 등 **라이선스 문서화 소스만** 인입. |
| **[KPI]** | 시드 고정의 **재현성**을 의학적 **구조 정확도**와 혼동·헤드라인 주장 **금지**. |
| **[CLAIM]** | `economic_edge_claim_allowed: false` — 「AI 해부 환각 완전 해결」 등 대외 성과·송출 **금지**. |

---

## §4. 재현 및 검증 노정

| 단계 | 산출물 | Done 조건 |
|------|--------|-----------|
| 1 | 본 정책 MD | 디스크 적재 |
| 2 | `rib55_angle_overlay_manifest_v1.json` | 스키마 + 1장 파일럿 행 |
| 3 | 오버레이 렌더 스크립트 | `py scripts/render_rib55_angle_overlay_v1.py --fetch-base --update-manifest` **exit 0** (파일럿 PNG: `docs/final/artifacts/rib55_overlay_pilot_ninth_rib_55deg_v0_latest.png`) |
| 3b | R1 L0/L1 ablation | `py scripts/run_rib55_l0_l1_ablation_v1.py` **exit 0** |
| 3c | R2 coord_v2 manifest | `py scripts/build_rib55_manifest_coord_v2_v1.py` → `py scripts/validate_anatomy_overlay_coord_v2_v1.py` **exit 0** |
| 4 | 원장 Adjudication | 수동 임상·각도 검수 서명 — **자동 게이트 해제 없음** |
| 4a | adjudication workflow | `py scripts/build_rib55_adjudication_workflow_v1.py` **exit 0** |
| 4b | record validate | `py scripts/validate_rib55_overlay_adjudication_v1.py --record-json <PATH>` |
| 4c | manifest apply | `py scripts/apply_rib55_overlay_adjudication_v1.py --record-json <PATH>` (template: `rib55_overlay_adjudication_record_v1.template.json`) |

**파일럿:** 9번 늑골 55° 오버레이 1장 — `docs/final/artifacts/rib55_overlay_pilot_ninth_rib_55deg_v0_latest.png` · 리포트 `reports/rib55_angle_overlay_render_v1_latest.json` · **원장 adjudication 전 송출 금지**.

**금지:** manifest·스크립트 없이 CONSTITUTION 「구현됨」 단정.

---

**Revision:** 2026-06-15 — v1 HYPO staging · pilot render script + PNG (step 3 exit 0; adjudication pending).
