# Git dirty triage — Infra v1

**Generated:** 2026-07-17 (local)  
**Scope:** `C:\workspace` after Nemotron venv SSOT (+7.9GiB reclaim)  
**Policy:** triage only — **no commit / stash / reset / push**

## 0) Vault gate (precondition)

| Check | Result |
|-------|--------|
| `Test-Path G:\` | **False** |
| `MKM_VAULT_ROOT` (User/Process) | set → `G:\공유 드라이브\MKM_DATA_VAULT\vault` (path **missing**) |
| Candidate vault roots | all **False** |
| `powershell -File scripts\push_local_artifacts_to_vault.ps1` | **exit 0** · `SKIP: Vault not mounted … - no push (not a C: fake vault).` |
| Fake C: production vault | **not created** |

**Tier-3 Human:** remount Google Drive / G: so `MKM_VAULT_ROOT` exists, then re-run vault push for real sync.

## 1) Dirty tree count

| Metric | Value |
|--------|------:|
| `git status --porcelain` lines | **170** |
| Modified / staged (non-`??`) | **170** |
| Untracked (`??`) | **0** |

(Commander note “dirty 167” ≈ this snapshot; count drifted +3.)

## 2) By path prefix

| Prefix | Count |
|--------|------:|
| `docs/` | 100 |
| `reports/` | 27 |
| `projects/` | 23 |
| `scripts/` | 15 |
| `.env.example` | 1 |
| `.gitignore` | 1 |
| `experiments/` | 1 |
| `research/` | 1 |
| `storage/` | 1 |

### docs/ detail

| Sub | Count |
|-----|------:|
| `docs/final/artifacts/` | 97 |
| `docs/final/CENTRAL_AGENT_MEMORY_V1.md` | 1 |
| `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` | 1 |
| `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md` | 1 |

### projects/ detail

| Sub | Count |
|-----|------:|
| `projects/no1kmedi/` | 16 |
| `projects/bitcoin-trading/` | 6 |
| `projects/mkm/` | 1 |

## 3) Risk classes

| Class | Paths / notes | Action |
|-------|---------------|--------|
| **High-risk review** | `.env.example` | Diff before any commit Ask (template only; still review) |
| **Do not commit** | `experiments/sasang-head-btrack/__pycache__/…cpython-311.pyc` | Exclude / clean; bytecode |
| **Data / generated (caution)** | `research/market_data/kospi_daily_external_yf.csv`, `storage/meta/mkm_ops_memory_index_v1.json`, bulk `docs/final/artifacts/*_latest.*`, many `reports/*` | Prefer curated Ask batches or leave dirty |
| **Large binary in dirty list** | **none matched** (no `.mp4`/weights in porcelain) | OK for this snapshot |
| **Secrets (`.env`, pem, DPAPI)** | **none matched** | OK for this snapshot |
| **Safe-ish intentional** | `scripts/*` (15), Nemotron WSL scripts (2), `.gitignore` | Good first Ask batches |

### Nemotron-related dirty (Infra continuity)

- `scripts/Verify-NvidiaNemotronWslReadiness_v1.ps1`
- `scripts/wsl/nemotron_local_setup_and_train_v1.sh`

## 4) Recommended commit batches (Ask only — not executed)

1. **Batch A — Infra Nemotron closeout (smallest):**  
   `scripts/Verify-NvidiaNemotronWslReadiness_v1.ps1` · `scripts/wsl/nemotron_local_setup_and_train_v1.sh` · optionally `.gitignore` + `scripts/push_local_artifacts_to_vault.ps1` if diffs are vault-SKIP related.
2. **Batch B — scripts ops (remaining ~12):**  
   other dirty under `scripts/` after A — one review pass, one commit Ask.
3. **Batch C — docs SSOT prose only:**  
   `docs/final/CENTRAL_AGENT_MEMORY_V1.md` + `docs/final/CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md` (± `docs/research/RESEARCH_OPEN_QUESTIONS_V1.md`).  
   **HOLD** bulk `docs/final/artifacts/` (97) + `reports/` (27) + `projects/*` until commander picks a product lane.

**Explicitly not recommended as one mega-commit:** all 170 lines.

## 5) Next Action (Infra)

1. Human: remount **G:** / vault → re-run `scripts\push_local_artifacts_to_vault.ps1` (expect non-SKIP sync).  
2. Or commander Ask: **Batch A** commit (no agent auto-commit).

## Repro

```powershell
Test-Path G:\
# MKM_VAULT_ROOT via [Environment]::GetEnvironmentVariable(..., 'User'|'Process') — do not dump secrets
powershell -File scripts\push_local_artifacts_to_vault.ps1   # exit 0 SKIP when G missing
git status --porcelain | Measure-Object -Line
```
