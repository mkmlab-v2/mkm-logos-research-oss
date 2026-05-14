# 연구·서사 인덱스 v1 (NotebookLM 노트북 목록 스냅샷)

**역할:** 클라우드 NotebookLM에 흩어진 **노트북 제목·ID·소스 개수**를 한곳에 두어, “연습장 흔적”을 **나중에** 레포로 긁어올 때 **검색 출발점**으로 쓴다.  
**성격:** **B 레이어(브리핑·역사)**. 구현·게이트·수치 SSOT는 **`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`**, **`docs/final/artifacts`**, **`MKM_CORE_THEORY_V1.md`**가 우선이며, 본 표는 **대체하지 않는다.**

**현행 스냅샷 시각 (UTC):** 2026-05-14  
**과거 전체 목록(41개 · 2026-04-12):** 아카이브로 분리 — `docs/final/artifacts/research_history_notebooklm_snapshot_2026-04-12.md` (운영 출발점 아님).

---

## 1) 현행 스냅샷 (MCP 로컬 라이브러리 · 운영 기본)

**수집:** MCP `get_health` (`authenticated=true`, `total_notebooks=3`) → `list_notebooks` / `get_notebook` (서버 `project-0-workspace-notebooklm`).  
**소스 개수·제목:** MCP `ask_question`(`notebook_id` 지정)으로 “소스 제목 나열 + Count” 프로브(NotebookLM / Gemini 2.5 합성). **웹 UI 소스 탭과 숫자가 1:1일 수는 없음** — 불일치 시 UI를 우선.  
**집합:** 아래는 **MCP에 등록된 라이브러리 노트**만 표시. Google 계정에 더 많은 노트가 있어도 **미등록이면 여기에 안 나온다.**

| 표시 이름 | MCP `id` | URL `…/notebook/<uuid>` | 소스 개수 (NL 프로브) | 비고 |
|----------|----------|-------------------------|------------------------|------|
| Ops Command Anchor (Fact-Lock) | `ops-command-anchor-fact-lock` | `347e5cbe-0ade-4615-9aac-8747d4fa644e` | **7** | 예전 아카이브 표의 `작전지휘부 Ops20260318`과 동일 UUID. `lg_hs_*` 등 발표·온보딩 자료 혼재 가능 → `TRACKC_BIZ` / 이벤트 노트와 중복 검토. |
| MKM Core Intelligence (Fact Focus) | `mkm-core-intelligence-fact-foc` | `aba1f8b1-be62-4367-ac7f-b1a997bb77d4` | **10** | 압축·SLA·코어 이론 중심 + `RESEARCH_HISTORY_V1.md`(B 인덱스) 포함 — `NotebookLM_sources_manifest.md` 기준 **유지 vs 별 노트** 검토만 권장. |
| SBA 2026 모두의 챌린지 발표평가 준비 | `sba-2026` | `b25977f3-1f92-4075-8dfe-d4074ca708a7` | **21** | OD327 청크·LG HS 자료·PPTX 등 — 이벤트·사업 브리핑 축; 종료 후 소스 정리·아카이브 후보. |

**웹 전용(미등록 · MCP `search_notebooks` TRACKC/MASTER 빈 결과, 2026-05-14):** `00_MASTER_TRACKC_BOARD_2026Q2` — 웹에서 Track C 보드로 운영 중이나 **MCP 로컬 라이브러리에는 없음**; 공유 URL 확보 후 `add_notebook` 권장.

**Ops MCP `ask_question` 타임아웃(2026-05-14):** `select_notebook` → Ops 활성화 후 `browser_options.timeout_ms=120000`에도 `Timeout waiting for response from NotebookLM` 재현 — 웹 UI에서 동일 노트 채팅 정상 여부·소스 수 확인 후 재시도.

---

## 2) 로컬·Vault (노트북과 자동 동일 아님)

- **H:** `H:\workspace\docs\`, `H:\workspace\daily\` — 레포 `C:\workspace`와 **경로 동일성 없음** (`CURRENT_OPS_SNAPSHOT.md` 참고).
- **G: Vault 인제스트 스냅:** `G:\공유 드라이브\MKM_DATA_VAULT\vault\h_drive_knowledge_ingest\2026-04-09\` 등.
- **레포 SSOT 미러:** `scripts/sync_notebooklm_sources_to_mkm_data_vault.ps1` → `vault\notebooklm_sources\`.

---

## 3) 갱신 규칙

1. 분기마다 또는 노트북 대량 추가·이름 변경 시: MCP `list_notebooks`(또는 동등) 재실행 후 **섹션 1 현행 표**를 갱신하고 **현행 스냅샷 시각**을 바꾼다. 이전 현행 본문을 보존하려면 같은 날짜 파일명으로 `docs/final/artifacts/research_history_notebooklm_snapshot_YYYY-MM-DD.md`에 복사한 뒤 덮어쓴다(선택).
2. 특정 노트에서 **레포로 옮길 파일**이 정해지면: 해당 파일 경로를 `docs/NotebookLM_sources_manifest.md` 또는 `$SourceFiles`에 추가하고 Vault 동기화한다.
3. 본 문서는 **에이전트 환각 방지용 목차**일 뿐, 노트북 안의 대화 본문을 대체하지 않는다.
4. 2026-04-12의 **41개 분류 표·전체 순서 표**는 고정 아카이브에만 둔다 — 현행 UUID/제목과 불일치할 수 있으므로 **열 링크 전에 섹션 1 또는 웹 UI**로 확인한다.

---

## 4) URL 패턴

`https://notebooklm.google.com/notebook/<notebook_id>`
