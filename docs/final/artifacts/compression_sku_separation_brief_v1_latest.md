# Compression SKU separation brief v1 [HYPO · internal only]

**SEND_GATE: HOLD** · **Track A ACTIVE untouched** · GTM % 약속 없음.

## SKU-COORD (coord)

- **용도:** bilateral pre-sync 장부 + pointer/inject ref wire — **원문 bulk MKM 서버 미수신**.
- **배포 노선 (blueprint):** Air-gap on-prem · edge encoder + control-plane relay.
- **경실:** 로컬 encoder SDK **미구현** · metadata(path/sha256/essence) 누출 가능 — 「zero exfiltration」 금지.
- **본 brief에서 제외:** MASK PoC 수치 · hybrid Tier A · Track A 47%.

## SKU-MASK (mask)

- **용도:** 마스킹 JSONL + v2 stateless/hybrid compress PoC.
- **라우터 SSOT:** `compression_hybrid_router_spec_v1.json` (spike sync: `sync_compression_hybrid_router_spec_from_spike_v1.py`).
- **Tier A gate:** public-open + wtt CS · mean pass **~86.7%** · `open_structured_long` **헤드라인 제외**.
- **STATUS (axis guard):** Tier A operational pass rate (~86.7%) — Golden-40·`open_structured_long` **별 축**; 코딩 deep pack 승인 지표 **아님**.

## Coding deep pack PoC (zone_f_code · seed)

- **템플릿 카탈로그:** `codebook/templates/zone_f_code_templates_v1.jsonl` (8 seeds) + manifest hash pin
- **Twin gate:** `compression_coding_deep_pack_gate_v1_latest.json` — `saving_rate` + `exact_restore_ok` (Jaccard **별도 축**)
- **재현:** `py scripts/build_compression_coding_deep_pack_gate_v1.py`
- **인접 증거(결정 아님):** `compression_candidate_pool_on_track_a_candidate_v1_latest.json`

## 축 분리 (FAIL-COMP-004)

| 축 | 허용 | 금지 |
|----|------|------|
| Golden-40 bench | ~47.4% `[internal signoff]` | customer SLA |
| v2 stateless proxy | ~6.4% `[HYPO]` | 「47% 달성」 |

**Fact-Lock:** `ltm_moat_factcheck_v1_latest.json` · `compression_sku_separation_brief_v1_latest.json`
