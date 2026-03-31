# AGENTS — 워크스페이스 에이전트 SSOT 포인터

**역할**: Cursor/Athena 에이전트가 먼저 읽는 **짧은 진입점**이다. 상세 규칙은 아래 파일이 주도한다.

## 필수 우선순위

1. **루트 `.cursorrules`** — 최상단 **TITAN · 자율 기동(Command-by-Negation)**. 예외가 아니면 권장 조치를 질문 없이 수행·사후 보고; 끝맺음은 [A]/[B] 선택 강요 없이 **완료 보고 + 잔여 리스크(있을 때만)**.
2. **`.cursor/rules/sovereign-central-command.mdc`** — Vault·NotebookLM·보안·운영(3문장 요약 + **§4 마무리**). §4에서 **폐지**: “Next Action 2가지”, `[A]`/`[B]`·a/b 강요. **대체**: TITAN 마무리 또는 고위험 시 **승인 범위만** 명시(루트 `.cursorrules`와 동일 방향).
3. **구현 팩트(환각 차단)**: `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` — 기획·NotebookLM만 보고 “이미 구현” 단정 금지.
4. **정체성 (Multi-Lens):** 단일 TOE·통일장 “완성” 선언 금지 — §1.1. 레짐·로고스·명리·외경은 **격벽·교차 참고** (§2.1·§4).

## 도메인 핸드오프(참고)

- 한의 원전·코호트: `docs/final/KOREAN_MEDICAL_CANON_INGEST_HANDOFF_2026-03-28.md` (라벨 A vs 원전 B 혼선 금지).
- NotebookLM 소스: `docs/NotebookLM_sources_manifest.md`.

## 12AI vs 코드북 도메인

- **12AI**는 Cursor 작업 라우팅용 **오케스트레이션 라벨**이다. 코드북 **도메인·샤드 개수**(파일럿 4존부터 확장 등)와 **1:1로 묶지 않는다.**
- 복잡·고위험 작업만 전문 서브에이전트로 분산하며, 보통 **2~4** 범위가 권장이다. 상세: `.cursor/skills/auto-12ai-routing/SKILL.md`.

## 경로

- 작업 루트: `C:/workspace` (Windows). Python 실행은 `py` 권장.
- **B-track 파일럿 벤치 SSOT:** `data/logos/btrack_pilot/bench/CANONICAL_BENCH_POINTER_V1.json` — 공식 의도 벤치는 포인터의 `canonical_builder_script`가 갱신하는 `a_track_eval.jsonl` / `b_track_eval.jsonl` 슬롯이다. direct·cross_ref 부트스트랩 빌더는 기본적으로 `*_direct_v1.jsonl` / `*_cross_ref_bootstrap_v1.jsonl`에 쓰며 canonical을 덮어쓰지 않는다. 경로 상수: `tools/myeongni/btrack_bench_paths.py`.
- **만세력 정밀(제2계층) SSOT 포인터:** `docs/final/MANSE_PRECISION_RUNTIME_POINTER_V1.json` — 에이전트 공식 배선은 Path B(MCP stdio, `athena-manseryeok`); 배치는 동일 엔진·per-row MCP 금지는 포인터 참조; 구현 팩트 표는 `CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` §3.4.
- 공유 SSOT 확인 경로(1순위): `G:\공유 드라이브\MKM_DATA_VAULT\vault\btrack_artifacts_verified` (미존재 시 `...\vault` 하위 경로 확인).
- B-track 핵심 산출물 승격(로컬 `reports/...` → G:): `scripts/push_local_artifacts_to_vault.ps1`
- 어휘·코퍼스 FACT-LOCK 계약: `docs/final/MASTER_Linguistic_Contract_2026.md` — 외부 사전 스테이징 `C:\workspace\vault\external_lexicon` → G: `...\vault\external_lexicon`: `scripts/setup/fetch_external_lexicons.ps1` (수신·MANIFEST) 후 `scripts/push_external_lexicon_to_vault.ps1` (승격)

## SSH Cursor · VPS 실매매 (전제)

- **SSH로 연 원격 폴더**를 열면 그쪽 `AGENTS.md` / `.cursor/rules`가 적용된다. 로컬 `C:/workspace`와 동시에 쓰면 **git 동기화**로 규칙을 맞춘다.
- 로컬 트리는 **개발·테스트·문서** 우선. **실매매 런타임**은 VPS 등 별도 배포본일 수 있으므로, 코드·설정이 자동 동일하다고 가정하지 않는다.
- 질문·답변에서 **로컬만**인지 **배포(VPS) 후**인지 구분한다. VPS 경로·PM2 앱 이름 등은 **지휘관이 확정한 값**으로만 서술하고, 미확인이면 “확인 필요”로 표기한다.
- 로컬 **SITREP → 공유 Vault 보급**(Windows, G: 마운트 시): `scripts/titan-sync.ps1` — **VPS 실매매 배포와는 별 작업**이다.
