# MKM Inter-Agent — 첫 번째 기계어 문장 (Worked Example v1)

**INTERNAL ONLY · pre-legal-send** — IR·쇼룸·대외 본문에 **그대로 복붙 금지**. 법무·`PUBLIC_FACING` v1.7 통과 후 발췌만.  
**머신 SSOT:** `mkm_inter_agent_first_message_worked_example_v1.json` (`py scripts/emit_mkm_inter_agent_first_message_worked_example_v1.py` 재생성)  
**상위:** `mkm_inter_agent_encoding_sota_map_v1.md` · **RQ-019** OPEN

---

## 0. 한 줄 정의

MKM 언어의 **첫 번째 기계어 문장** = 짧은 입력 텍스트가 **v2 Trust Packet**으로 압축되고, **`POST /v2/expand`는 패킷만** 받아 stub의 `reconstructed_text`를 되돌리는 **기계 roundtrip**이다. 이것은 **인간 무손실 번역이 아니다.**

---

## 1. 입력 (Sample)

```
사상의학 체질 분류 예시. MKM inter-agent message rail demo.
sasang taeeum soeum myeongri logos atom_id trust_packet.
```

---

## 2. 압축 — `POST /v2/compress` (`loss_profile: semantic_general`)

| 필드 | 이번 실측 값 (2026-05-18 UTC) | 의미 |
|------|------------------------------|------|
| `compressed_text` | `사상의학 체질 message sasang myeongri MKM rail soeum` | 증류 본문 |
| `residual_meta.mk_stub_v2.reconstructed_text` | (stub 엔진 재조립문) | expand가 반환하는 기계 복원 원천 |
| `residual_meta.mk_stub_v2.global_token_saving_rate` | **~0.619** (이 샘플) | 이 샘플 토큰 프록시 절감 — **Track A 동결 ~0.47과 혼동 금지** |
| `residual_meta.mk_stub_v2.reconstruction_fidelity_jaccard` | **~0.882** (이 샘플) | 입력 vs stub 재조립 Jaccard |
| `router_meta.shard_id` | `zone_a_scm` | 도메인 라우터 결과 |
| `content_fingerprint` | `b3cec1bac0ef573a2b7e07ce21612f9e` | 패킷 지문 |
| `compression_metrics` | `token_in: 21`, `token_out: 8` | stub 프록시 카운트 |

전체 JSON(발췌): `docs/final/artifacts/mkm_inter_agent_first_message_worked_example_v1.json` → `compress`.

---

## 3. 기계 복원 — `POST /v2/expand` (packet only)

| 검증 | 결과 |
|------|------|
| 요청 본문에 `original_text` | **없음** (`original_text_on_expand_request: false`) |
| `expand` 출력 == `mk_stub_v2.reconstructed_text` | **`true`** (`expand_equals_stub_reconstructed`) |
| 입력 vs expand Jaccard (이 샘플) | **~0.882** |

**의미:** 에이전트 A→B는 **패킷(JSON)** 만 주고받아도, B stub은 **동일 stub 재조립문**을 받을 수 있다(M1). **원문 바이트 동일 복원은 주장하지 않는다.**

---

## 4. 인간 복원 — L1 역추론 (`research_only`)

| 지표 | 값 | 출처 |
|------|-----|------|
| `avg_exact_restore_rate` | **~57.87%** | `l1_inverse_decoder_spike_test_summary_latest.json` |
| 범위 (스파이크) | ~53.9% – ~61.7% | 동일 |
| 대외 한 줄 | 무손실·100% 복원 **미주장** | status JSON `m3.public_copy_draft.ko` |

L1 **msgpack wire** (`POST /v1/research/l1_side_channel/wire`)는 본 예제 범위 밖 — `mkm_inter_agent_wire_profile_v0.json` `side_channel.research_only: true`.

---

## 5. 4계층 ↔ 이 예제

| 계층 | 이 예제에서 보이는 것 |
|------|----------------------|
| 어휘 (41k) | `evaluate_report` + lexicon bridge가 압축·must_keep에 관여 (전체 `atom_id` 나열은 본 1페이지 생략) |
| 문법 (Trust Packet) | §2–§3 패킷 필드 |
| 전송 (L1 wire) | **미포함** (연구 레일) |
| 번역 (L1 decoder) | §4 — **확률·연구**, 기계 roundtrip과 **분리** |

---

## 6. 한계 박스 (Fact-Lock)

- **상용 SLA 없음** · **업계 표준(TCP/IP) 채택 주장 없음**
- **Track A 동결 벤치** (~47% 절감, ~0.90 Jaccard)와 **이 샘플 수치**를 한 슬라이드에 넣지 말 것
- **쇼룸 헤드라인**에 L1 58%·예언 적중·압축 KPI **합선 금지**
- RQ-019: `rq_019_milestones_core_ready` ≠ RQ **CLOSED** (법무·Whitepaper 승격 전)

---

## 7. 재현 (in-process)

```bash
py scripts/emit_mkm_inter_agent_first_message_worked_example_v1.py
py -m pytest tests/test_emit_mkm_inter_agent_first_message_worked_example_v1.py tests/test_compression_token_api_v2_stub.py -q
```

---

## 8. 살아있는 HTTP 왕복 (로컬 stub · IR/내부 증명용)

**전제:** 저장소 루트 `C:\workspace` · stub 기동 후 다른 터미널에서 curl.

### 8.1 Stub 기동

```bash
py -m uvicorn scripts.compression_token_api_v2_stub:app --host 127.0.0.1 --port 8011
```

### 8.2 `POST /v2/compress`

```bash
curl -s -X POST http://127.0.0.1:8011/v2/compress ^
  -H "Content-Type: application/json" ^
  -d @docs/final/artifacts/fixtures/mkm_inter_agent_compress_request_v1.json
```

**실측 요약 (2026-05-19):** `token_in` 21 → `token_out` 8 · `savings_ratio` ~0.619 · `compressed_text`는 증류 본문 · `residual_meta.mk_stub_v2`에 기계 재조립문·Jaccard 보관.

### 8.3 `POST /v2/expand` (packet only — `original_text` 없음)

```bash
curl -s -X POST http://127.0.0.1:8011/v2/expand ^
  -H "Content-Type: application/json" ^
  -d @docs/final/artifacts/fixtures/mkm_inter_agent_expand_request_v1.json
```

**실측:** `expand` 출력 == `mk_stub_v2.reconstructed_text` · `integrity_flags.source` = `mk_stub_v2`.

**박제 JSON:** `docs/final/artifacts/mkm_inter_agent_first_message_live_http_v1.json` (compress+expand 응답 전문).

**schema:** `mkm_inter_agent_first_message_worked_example_v1` · **generated:** 2026-05-19
