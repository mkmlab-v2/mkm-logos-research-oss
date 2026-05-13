# LOCAL_MACHINE_POINTER v1 — 템플릿 (Git 추적)

**역할:** PC·드라이브마다 다른 경로(bare Git, 추가 클론, Vault 마운트 등)를 **레포 공통 SSOT가 아닌 한 곳**에만 적는다.  
**`CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md`에는 절대 경로를 헌법처럼 넣지 않는다** — 클론·CI·타 PC와 충돌한다.

## Git에 올리지 않는 파일

| 파일 | Git |
|------|-----|
| **이 파일** (`…V1.template.md`) | 추적됨 — 복북용 뼈대만 커밋 |
| **`docs/final/LOCAL_MACHINE_POINTER_V1.md`** | **비추적** — 아래 내용을 이 이름으로 저장. `.gitignore`에 등록됨. **원격 푸시되지 않음.** |

한 번 설정: 이 템플릿을 복사한다.

```text
copy docs\final\LOCAL_MACHINE_POINTER_V1.template.md docs\final\LOCAL_MACHINE_POINTER_V1.md
```

(또는 동일 내용으로 `LOCAL_MACHINE_POINTER_V1.md`를 새로 만든 뒤) 표만 본인 경로로 고친다. **시크릿·API 키·토큰은 넣지 않는다** — `.env` 유지.

---

## 채우기 (예시 행은 삭제하고 본인 값만)

| 키 | 값 (본인 PC 전용) |
|----|-------------------|
| `git_bare_primary` | 예: `E:\Git\repos\mkm-destiny-ai-41e38ec6.git` — `AGENTS.md` 일인 개발 절의 **조건부 예시**와 같은 배치일 수 있음. 없으면 비움. |
| `git_remote_internal_name` | 예: `internal` / `gitea` |
| `extra_clone_roots` | 여러 줄: 다른 worktree·클론 루트 |
| `mkm_data_vault` | 예: `G:\공유 드라이브\MKM_DATA_VAULT` — 미마운트면 비움 |
| `ollama_models_dir` | Ollama blobs가 실제로 있는 디렉터리(예: `F:\…` 또는 `C:\Users\…\.ollama`를 정션으로 옮긴 **실타겟**). 레포·CI에는 넣지 말 것. |
| `windows_c_cleanup_note` | 선택: C: 루트 잔재 정리는 레포 스크립트 `scripts/Invoke-CRootInstallerLeftoversCleanup_v1.ps1` / `scripts/Invoke-CRootAmdInstallerCacheCleanup_v1.ps1`(관리자) — 실행 일시·결과만 여기 한 줄로 적어도 됨. |
| `notes` | 한 줄 메모 (선택) |

---

## 에이전트용 한 줄

- `LOCAL_MACHINE_POINTER_V1.md`가 있으면 **머신 로컬 경로 질문은 이 파일을 1순위**로 읽는다.
- 없으면 **공통 SSOT만** 따르고, PC 전용 경로는 “확인 필요”로 둔다.

**스키마:** `local_machine_pointer_v1` (비공식 마크다운 표; JSON 스키마 없음)
