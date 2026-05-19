# Track C 쇼룸 · Topology + Meaning Graph — 5분 B2B 데모 대본 (v1)

- **generated_at_utc:** 2026-05-19 (session)
- **status:** `DRAFT_AUTO` — 법무·대외 send 전 내부 미팅·랩탑 투사 전용
- **tone:** 70% 과제 직결 · 20% 운영 성숙도 · 10% 장기 비전 힌트 (`AGENTS.md` 발표 설득 모듈)
- **Fact-Lock:** 수치·통과 여부는 본 대본이 아니라 디스크 아티팩트·`reports/track_c_b2b_meeting_pack_readiness_v1_latest.json`만 SSOT

---

## 0) 프리플라이트 (데모 30초 전)

**탭 순서 (왼쪽→오른쪽):**

1. `public_showroom_topology_radar_v1.html` — Risk Topology Radar  
2. `public_showroom_meaning_topology_graph_v1.html` — Meaning topology graph (**신규**)  
3. `public_showroom_logos_research_v1.html` — Logos research slice (백업)

**로컬 스테이징 (VPS 전):**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-ShowroomTrackCPublishRoutine_v1.ps1
# nginx 미러 갱신 시: ... -ApplyRecommendedNginx
```

**화면에 항상 보이게 할 배지:** `[HYPO]` · `research_only` · `NON_GATING` · `no_trade_signals`

**금지 한 줄 (입 열기 전):** 투자 권유·매매 지시·종교적 진리·성과 보장 단정 금지.

---

## 0b) 병렬 점검 (2026-05-19 · 자동 · publish 루틴 후)

| 항목 | 상태 |
|------|------|
| B2B 미팅 팩 readiness | `ready_for_internal_meeting=true` · `reports/track_c_b2b_meeting_pack_readiness_v1_latest.json` |
| 듀얼 호스트 스모크 | `reports/showroom_trust_viz_public_chain_smoke_latest.json` → ok |
| API latest | `showroom-20260519T095211-baabd38b` · `system_status=online` · `public_signal_direction=HOLD` |
| meaning slice | 35 nodes / 54 edges |
| 일일 예약 | `Showroom-TrackC-Publish-Daily` · **첫 실행 OK** (`last_task_result=0`, 2026-05-19 18:52 KST) |
| 주간 nginx | `Showroom-TrackC-Nginx-Weekly` · **첫 실행 OK** (`last_task_result=0`, 2026-05-19 19:00 KST) |
| 원클릭 헬스 | `Invoke-MkmPersonaHealth_v1.ps1 -Persona ShowroomTrackCHealth` |

---

## 1) 오프닝 (30초)

> "오늘은 '예언 챗봇'이 아니라, **관측 가능한 위험 토폴로지**와 **의미 연결망 스냅샷**을 어떻게 엔터프라이즈 PoC에 붙일 수 있는지 보여드리겠습니다.  
> 모든 화면은 **연구·관측 레일**이며, 귀사 운영 게이트나 주문 트리거를 대체하지 않습니다."

---

## 2) Act 1 — Risk Topology Radar (90초)

**URL:** `https://jemaai.cloud/public_showroom_topology_radar_v1.html` (또는 스테이징 동명 HTML)

**말하기:**

1. "첫 화면은 **레이더 메타포**입니다. CALM / WATCH / ELEVATED는 **공개 이벤트 스트림**의 관측 상태이지, 매수·매도 신호가 아닙니다."
2. (잠시 대기) "API가 살아 있으면 상단에 연결 상태가 보이고, 없으면 **스냅샷 JSON**으로 동일 레이아웃을 유지합니다 — 데모 끊김 방지용입니다."
3. **중앙 코어 또는 WATCH 링 클릭** → deep-dive 패널 오픈.  
   "여기서 Logos **테마 슬라이스** 몇 줄만 붙습니다. 전체 성경 해석 엔진이 아니라, **쇼룸용 얇은 슬라이스**입니다."

**전환 한 줄:**

> "레이더가 '지금 판의 색'이라면, 다음 화면은 그 판 뒤에 깔린 **실제 그래프 데이터**입니다."

---

## 3) Act 2 — Meaning Topology Graph (2분 30초) ★ 핵심

**URL:** `https://jemaai.cloud/public_showroom_meaning_topology_graph_v1.html`

**말하기:**

1. "이 페이지는 백엔드 `bible_meaning_graph` JSONL에서 뽑은 **부분 그래프**입니다. insight 후보 **허브 점수**로 시드를 고르고, 노드·엣지 수를 캡해 브라우저에 올립니다."
2. **라벨 가리키기:**  
   - 주황 **imperial transition** (theme)  
   - 청록 **empire transition** (regime)  
   - 녹색 **Dan.2.10 ~ Dan.2.19** (verse 허브)  
   "고객님께는 '추상 AI'가 아니라 **구절·테마·레짐이 한 망 위에 있다**는 그림이 먼저 들어가야 합니다."
3. **엣지 색 (짧게):**  
   - 금색 계열 = theme/regime 투영  
   - 녹색 계열 = cross-lens 확인 (다국어 코퍼스 연결)  
   "아직 학술적 완성도를 주장하는 단계는 아니고, **연구 스냅샷**입니다."
4. **노드 클릭** → 우측 Node detail에 `kind` · `ref` · `hub_score`.  
   "심사 시에는 **클릭 한 번으로 근거 노드**를 보여드릴 수 있습니다."
5. (선택) 노드 드래그 후 멈춤 — "시뮬레이션은 안정화 후 **CPU를 쓰지 않도록** 멈춥니다. 장시간 미팅에 적합합니다."

**증거 한 줄 (과장 금지):**

> "오늘 슬라이스는 **35 nodes / 54 edges** 스냅샷이며, 생성 시각은 화면 하단 `generated_at_utc`를 보시면 됩니다."

---

## 4) Act 3 — Logos Research Slice 백업 (60초)

**URL:** `https://jemaai.cloud/public_showroom_logos_research_v1.html`

**말하기:**

1. "그래프가 부담되시면, 동일 레일의 **테마 카드 뷰**로 전환할 수 있습니다."
2. golden anchor · semantic nodes · governance mapping — "**해설용 NON_GATING**"임을 다시 강조.
3. "B2B 딥다이브 문서는 미팅 팩 `track_c_b2b_logos_lens_appendix_v1_latest.md`와 compression appendix를 PoC SOW에 첨부합니다."

---

## 5) 클로징 (30초)

> "정리하면, MKM Track C 쇼룸은 **(1) 관측 레이더 (2) 의미 그래프 실데이터 (3) 서면 B2B 팩** 세 층입니다.  
> 다음 단계는 **90일 PoC SOW** 범위에서 귀사 데이터 경계 안에 그래프 시드를 맞추는 것이고, **실매매·본선 트리거 합선은 하지 않습니다.**  
> 질문 주시면, 아티팩트 경로와 재현 명령으로 답변드리겠습니다."

---

## 6) Q&A 즉답 카드 (15초 구조: 결론 → 근거 → 제한)

| # | 질문 | 답변 골격 |
|---|------|-----------|
| 1 | 라이브인가요? | 스냅샷 + 선택 API 폴링. **연구·관측**이며 주문 트리거 아님. |
| 2 | 성경 해석 정확도는? | **단정하지 않음.** `[HYPO]` 연구 레일; 승격은 별도 게이트·휴먼. |
| 3 | 그래프 전체를 보나요? | **아니요.** 허브 시드 + 캡(기본 48노드). IP·성능 보호. |
| 4 | 투자 신호인가요? | **아니요.** `no_trade_signals` · NON_GATING. |
| 5 | 레이더와 그래프 관계? | 레이더=관측 메타·연출; 그래프=의미망 **실데이터 슬라이스**. |
| 6 | 재현 방법? | `py scripts/build_showroom_meaning_topology_graph_slice_v1.py` + 체인 7/7. |
| 7 | 법무 검토? | 대외 send 전 `ready_for_external_send` 게이트; 오늘은 **내부 미팅** 전제. |
| 8 | Track A와 합치나요? | **자동 합선 없음.** B-track → A 승격은 별도 Fact-Lock. |
| 9 | 왜 Daniel 구절만? | 현행 insight 후보 허브가 해당 클러스터 — **시드 교체 가능**. |
| 10 | PoC 다음 산출물? | 맞춤 시드·엣지 타입 리포트·주간 스냅샷 갱신 (SOW 범위). |

---

## 7) 첨부 포인터 (슬라이드 각주용)

| 자료 | 경로 |
|------|------|
| 미팅 팩 인덱스 | `docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md` |
| Combined offer | `docs/final/artifacts/track_c_combined_b2b_offer_onepager_v1_latest.md` |
| 그래프 슬라이스 스키마 | `docs/final/schemas/showroom_meaning_topology_graph_slice_v1.schema.json` |
| PUBLIC_FACING 체크리스트 | `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md` v1.7 |

---

## 8) 면책 (모든 덱·이메일 하단)

> Not investment advice. No buy/sell instructions. Logos / meaning-graph layers are `[HYPO]` and `[NON_GATING]`. Core formulas not disclosed. Observational showroom only.
