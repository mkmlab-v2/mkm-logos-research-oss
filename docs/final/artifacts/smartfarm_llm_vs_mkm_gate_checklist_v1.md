# 스마트팜 LLM 가능 범위 vs MKM 게이트 체크리스트 v1

**schema:** `smartfarm_llm_vs_mkm_gate_checklist_v1`  
**status:** `internal_ops` — 대외·투자·가입자 카피에 **그대로 붙이지 않음**  
**audience:** 지휘관 · 개발 · 벤더 협의 · PoC 범위 판단  
**related:** `AI_SMARTFARM_CONTROL_SAFETY_POLICY.yaml` · `AI_SMARTFARM_OPERATION_RESPONSIBILITY_1P.md` · `smartfarm_qubics_contract_signed_v1.json` · `smartfarm_geumsan_faas_master_plan_v10_lite_v1.md`

---

## 0. 한 줄

**큐빅스 MQTT/HTTP 연동·데모 UI는 LLM+일반 개발로 빠르게 가능.**  
**농장에 자동관수를 맡기려면 MKM 안전·책임·현장 게이트가 필수** — LLM 유무와 무관.

---

## 1. 판정 규칙 (3초)

| 질문 | YES → | NO → |
|------|--------|------|
| 물리 밸브/펌프가 실제로 움직이나? | **MKM 게이트** | LLM PoC 구간 가능 |
| 사람 없이 auto가 다음 관수를 확정하나? | **MKM 게이트** | 보조·초안만 |
| 가입자·사장·대외에 품질·안전을 암시하나? | **MKM 게이트 + PUBLIC_FACING** | 내부 메모 |
| 벤더 매뉴얼·견적·계약 SSOT와 충돌하나? | **Fact-Lock·사람 확인** | LLM 초안 OK |

---

## 2. LLM만으로 (또는 LLM 주도) **가능** — `research_only` / PoC

| # | 작업 | 산출 예 | 비고 |
|---|------|---------|------|
| L1 | PDF·메일 → 프로토콜 요약 | topic/payload 표 | `reports/qubics_pdf_extract_latest.json` 대조 |
| L2 | MQTT subscribe / publish **스텁** | dry-run pass | `check_smartfarm_qubics_mqtt_uplink_dry_run_v1.py` |
| L3 | JSON normalize·manifest 초안 | D301→zone | cid는 현장 uplink 후 |
| L4 | FastAPI ingest·대시보드 **목업** | 8020 stub | 상용 ≠ stub |
| L5 | 견적·회신 메일 **초안** | 큐빅스 확인 3문항 | 발송 전 사람 검토 |
| L6 | NotebookLM·Gemini **브레인스토밍** | 구역·작물 아이디어 | 농업 판단 근거 아님 |

**허용 문구:** 「연동 PoC」「데모」「내부 검증」  
**금지 문구:** 「완성된 스마트팜」「AI가 알아서 관수」「안전 보장」

---

## 3. MKM이 **막아야 하는** — 운영·상용·현장

| # | 게이트 | SSOT | 미통과 시 |
|---|--------|------|-----------|
| G1 | **명령 우선순위** emergency > 현장 > 원격 > auto | `AI_SMARTFARM_OPERATION_RESPONSIBILITY_1P.md` §4 | auto 금지 |
| G2 | **동시 다채널 개방 금지**·순차 펄스만 | `smartfarm_geumsan_6channel_valve_mapping_v1.json` | dispatch 차단 |
| G3 | **통신 끊김·stale** → auto_stop | `AI_SMARTFARM_CONTROL_SAFETY_POLICY.yaml` `stale_data_action` | 관수 중단 |
| G4 | **일일·회당 관수 상한** | 동 policy `hard_limits` | command reject |
| G5 | **비 게이트** (강우 예보 등) | `rain_gate` | skip/delay |
| G6 | **배양액 배치 게이트** | `fermentation_batch_gate` | nutrient ch 차단 |
| G7 | **릴레이 ACK** evnt `"즉각 제어 완료"` | MQTT 프로토콜 PDF §6 | retry 후 alert |
| G8 | **comm_ok / max_data_gap** | 900s 기본 | auto 평가 HOLD |
| G9 | **책임 경계** MKM=SW·로그 / 사장=현장·통신·CAPEX | FaaS V10-lite §1 | 대외 카피 혼선 금지 |
| G10 | **Track A·실매매** 합선 금지 | `.cursorrules` 투트랙 | research_only 유지 |
| G11 | **현장 Go-Live** 72h 센서 안정·수동 dry-run | Operation Responsibility §5 | Phase 승격 불가 |
| G12 | **cid·브로커 커미셔닝** manifest 확정 | `smartfarm_qubics_device_manifest_v1.json` | live publish 금지 |

---

## 4. 큐빅스( CoCoNET ) 한정 메모

| 구분 | LLM이 흔히 하는 일 | MKM이 확인하는 일 |
|------|-------------------|------------------|
| 프로토콜 | `qbsv4/downlink` + `req`/`cmd` 코드 생성 | PDF 2026-06-18·pytest·phase0 exit 0 |
| 장비명 | D301/D302/D202 표 정리 | **토픽은 cid** — manifest commission |
| 제어 의미 | ON/OFF 단순 매핑 | PDF: 0x01=접점연결(ON), 0x02=분리(OFF) · ch3 역할 현장 |
| 인프라 | “MQTT 붙이면 끝” | Mosquitto·G300 IP·LTE·상시전원(견적 조건) |
| 면책 | 생략 | 통신 품질·자가설치 — `smartfarm_qubics_contract_signed_v1.json` |

---

## 5. 승격 체크 (PoC → 현장 파일럿)

- [ ] `run_smartfarm_qubics_phase0_chain_v1.ps1` exit 0  
- [ ] `smartfarm_qubics_mqtt_uplink_dry_run_latest.json` verdict pass  
- [ ] manifest에 D301/D302/D202 **실 cid** (not `TBD_COMMISSIONING`)  
- [ ] ch1 relay dry-run + evnt ACK 1회 이상  
- [ ] `AI_SMARTFARM_CONTROL_SAFETY_POLICY.yaml` limit·rain·batch 게이트 코드 경로 확인  
- [ ] 사장·가입자 대외 문구 — `PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`  

**전부 체크 전:** auto 관수·대외 “스마트팜 완성” 주장 금지.

---

## 6. 재현 명령

```powershell
powershell -File scripts\run_smartfarm_qubics_phase0_chain_v1.ps1
py scripts/check_smartfarm_qubics_mqtt_uplink_dry_run_v1.py
```

---

**boundary_ack:** 내부 운영 판정용. 벤치 KPI·Track A·live trading gate 아님.
