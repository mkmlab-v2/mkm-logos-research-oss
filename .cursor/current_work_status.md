# 📌 현재 작업 상태 (채팅창 간 공유)

**목적**: 다른 채팅창이 "지금 뭘 하고 있는지" 파악할 수 있도록 하는 **유일한** 진실 소스.
**규칙**: 작업 시작/중요 전환/완료 시 이 파일을 **반드시** 업데이트한다.

**마지막 검증일 (SSOT 정합)**: 2026-03-29

---

## ⚠️ 왜 다른 채팅이 작업을 못 파악하나?

- **Cursor는 채팅창마다 대화 컨텍스트가 완전히 분리**됩니다. MCP가 정상이어도 "다른 채팅의 대화 내용"은 전혀 전달되지 않습니다.
- 다른 채팅이 알 수 있는 방법은 **이 파일(또는 아래 연동 문서)을 읽는 것**뿐입니다.
  → 이 파일을 갱신하지 않으면, 다른 채팅은 **항상** "모른다".

---

## 📋 지금 이 워크스페이스에서 진행 중인 작업

| 채팅 구분 | 담당/주제 | 현재 작업 | 상태 | 마지막 업데이트 |
|-----------|-----------|-----------|------|-----------------|
| memory-organization | MKM Memory 구조 정리 | hot / warm / archive 기준 적용, web_docs 파생 인덱스와 logs 기록물 정리 | 진행 중 | 2026-03-18 |
| vault-organization | MKM Data Vault 구조 정리 | 활성/참조/아카이브 경계 정의, 상태 파일 정리, 인덱싱 범위 축소 | 완료 | 2026-03-18 |
| mcp-routing | Cursor MCP 경로/권한 점검 | `C:/workspace` + `G:/공유 드라이브/MKM_DATA_VAULT` 분리 확인 | 진행 중 | 2026-03-18 |
| ssot-coord | 멀티채팅 SSOT 정합 | `current_work_status.md` / `scratchpad.md` 팩트체크·과장 완료 표기 정리 | 완료 | 2026-03-29 |

---

## 🔍 팩트체크 메모 (2026-03-29, 저장소 기준)

- **Sovereign Image Bridge**: `scripts/sovereign_image_bridge.py` **미존재**, `/generate-style-prompt` 라우트 **미발견**. `.cursor/scratchpad.md`에 있던 “1~4단계 완료”는 **저장소와 불일치** → 백로그·계획으로 취급.
- **Sovereign Fit**: `SovereignFitPanel.tsx`, `MKMStudyApp.tsx` 통합 등 **해당 파일 미발견**. 동일하게 **미구현·계획**으로 취급.

---

## 🔗 연동 문서 (다른 채팅이 읽으면 좋은 문서)

- **MKM Data Vault 정리안**: `docs/final/MKM_Data_Vault_Organization.md`
- **MKM Memory 정리안**: `docs/final/MKM_Memory_Organization.md`
- **MCP 설정**: `C:\workspace\.cursor\mcp.json`

---

## ✅ 다른 채팅에서 작업 파악하는 방법

1. **이 파일을 @멘션**: `@.cursor/current_work_status.md` 로 열어 두고 질문하면, 이 채팅이 위 표를 보고 다른 채팅 작업을 반영할 수 있습니다.
2. **연동 문서 @멘션**: `@docs/final/MKM_Data_Vault_Organization.md` 또는 `@docs/final/MKM_Memory_Organization.md` 로 기준을 바로 읽을 수 있습니다.

**정리**: MCP가 정상이어도 채팅 간에는 **파일로 써 둔 것만** 공유됩니다. 이 파일(또는 연동 문서)을 갱신해야 다른 채팅이 작업을 파악할 수 있습니다.
