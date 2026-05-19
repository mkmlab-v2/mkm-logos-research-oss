# MKM Inter-Agent Message Rail — IR·과제용 스니펫 (v1)

**INTERNAL ONLY · counsel-cleared (`LC-2026-05-19-RQ019-CLEARED`)** — 대외 **발송·게시마다** `PUBLIC_FACING` v1.7 금지어 체크 **필수** (법무 일괄 승인 ≠ 개별 채널 면책 생략).  
**근거:** `mkm_inter_agent_first_message_live_http_v1.json` · worked example MD · `mkm_inter_agent_encoding_status_latest.json` (`rq_019: CLOSED`)

---

## 대외 한 줄 (KO · 권장)

> MKM은 **측정 가능한 에이전트 간 메시지 레일 초안(Draft of a measurable agent-to-agent message rail)**을 구축 중입니다. **41k-class 렉시콘**과 **도메인 통제 압축** 위에 **v2 Trust Packet(초안)**으로 compress/expand 왕복을 **로컬 스텁·pytest·curl**로 재현했으며, **상용 SLA·업계 표준 채택·무손실 인간 통역은 주장하지 않습니다.**

## 대외 한 줄 (EN)

> MKM is building a **draft measurable agent-to-agent message rail**: a **41k-class lexicon rail** and **governed compression** under a **Trust Packet (draft)**, with **reproducible compress→expand roundtrips** via stub, pytest, and curl. We do **not** claim production SLA, industry-standard adoption, or lossless human translation.

---

## 증거 3종 (슬라이드 1장)

| # | 무엇 | 숫자·판정 | SSOT |
|---|------|-----------|------|
| 1 | **기계 왕복** (packet-only expand) | `expand_equals_stub_reconstructed: true` | `mkm_inter_agent_first_message_live_http_v1.json` |
| 2 | **Track A 동결 벤치** (별 축) | token saving **~47%** · Jaccard **~0.90** · 4D bridge **OFF** | `MULTILENS_ULTRA_COMPRESSION_ACTIVE_REPORT_V1.json` |
| 3 | **인간 역복원(L1)** (`research_only`) | exact restore **~57.9%** — 100% **미주장** | `l1_inverse_decoder_spike_test_summary_latest.json` |
| 4 | **건강 B-track 라우팅** (지휘관 승인 · INTERNAL) | `routing_profile=b_track_domain_relax` · Track A 벤치 **미대체** | `mkm_inter_agent_health_domain_commander_approval_v1_latest.json` |

**금지:** 위 2·3을 한 슬라이드 KPI로 합치지 말 것. 이 샘플 curl의 **~62% 절감**은 Track A **47%가 아님**. 건강 완화 캡은 **에이전트 간 B-track 전용**이며 40-case global **~46.8%**로 Track A 승격 조건(0.47 floor) **미충족**.

---

## 라이브 데모 (30초 · 내부 시연)

```bash
py -m uvicorn scripts.compression_token_api_v2_stub:app --host 127.0.0.1 --port 8011
curl -s -X POST http://127.0.0.1:8011/v2/compress -H "Content-Type: application/json" -d @docs/final/artifacts/fixtures/mkm_inter_agent_compress_request_v1.json
curl -s -X POST http://127.0.0.1:8011/v2/expand -H "Content-Type: application/json" -d @docs/final/artifacts/fixtures/mkm_inter_agent_expand_request_v1.json
```

---

## 면책 (슬라이드 각주)

- Stub / draft contract — **not** production API or SLA.
- **Not** TCP/IP, **not** a finished lingua franca, **not** beats-SOTA-papers claim.
- RQ-019 **CLOSED** (internal ops · `LC-2026-05-19-RQ019-CLEARED`) — **not** industry-standard adoption or production SLA.
- Commander approved **B-track health/hangul caps** for inter-agent v2 routing only — **not** Track A bench replacement.

**schema:** `mkm_inter_agent_ir_snippet_v1` · **generated:** 2026-05-18 · **counsel:** LC-2026-05-19-RQ019-CLEARED · **rq_019:** CLOSED
