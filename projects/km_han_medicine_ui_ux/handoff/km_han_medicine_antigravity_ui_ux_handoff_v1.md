# KM 한의학 UI/UX Prompt Pack — Antigravity → Cursor IDE 핸드오프

**updated:** 2026-07-05  
**bundle root:** `projects/km_han_medicine_ui_ux/`  
**zip (reproducible):** `reports/km_han_medicine_ui_ux_v1.zip`

---

## 1. 주요 산출물

| 파일 | 설명 |
|------|------|
| `projects/km_han_medicine_ui_ux/` | 핸드오프 번들 (README, SETUP, prompts, ssot, mocks, cursor checklist) |
| `reports/km_han_medicine_ui_ux_v1.zip` | 공유용 ZIP |
| `scripts/Prepare-KmHanMedicineBundle_v1.ps1` | 번들 폴더 동기화 + mock Pack* dirs |
| `scripts/Build-KmHanMedicineUiUxHandoffZip_v1.ps1` | ZIP 생성 |
| `reports/km_han_medicine_antigravity_ui_ux_prompt_v1.md` | Antigravity 프롬프트 팩 (Master Brief + Pack A supplement + E/F/G) |
| `docs/final/artifacts/jemaai_antigravity_design_prompt_packs_v1_latest.md` | SSOT 포인터 (Pack E/F/G) |

---

## 2. 번들 동기화 + ZIP 빌드 (로컬)

```powershell
cd C:\workspace
# 2a. 번들 폴더 동기화 (prompts/ssot/mocks Pack* 디렉터리)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Prepare-KmHanMedicineBundle_v1.ps1
# 2b. ZIP (선택: Prepare -BuildZip 한 번에)
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\Build-KmHanMedicineUiUxHandoffZip_v1.ps1
```

- **Prepare:** `projects/km_han_medicine_ui_ux/` — SSOT는 `reports/`·`docs/final/artifacts/`에서 복사 ( **`C:\workspace\prompts\` 아님** )
- **Build 출력:** `reports/km_han_medicine_ui_ux_v1.zip`
- **제외:** `build/`, `.gradle/`, `.idea/` (스크립트가 staging만 사용)
- **배포 URL:** 내부 공유 드라이브 업로드 후 아래에 기록 (지휘관 수동)

| 배포 | URL |
|------|-----|
| ZIP | _(미업로드 — 로컬 `reports/km_han_medicine_ui_ux_v1.zip` · 2026-07-05 빌드 확인)_ |

---

## 3. Cursor IDE 작업 흐름

1. ZIP 다운로드 → `C:\workspace\projects\km_han_medicine_ui_ux`에 압축 해제 (또는 repo에 이미 있으면 생략)
2. `README.md` · `SETUP.md` 확인
3. Antigravity 산출물을 `mocks/`에 배치 (Figma export / HTML)
4. Pack **A supplement → E → F → G** 순으로 mock 검증
5. `cursor/MERGE_CHECKLIST.md` 따라 CSS·presentational TSX만 merge
6. Gate exit 0 후 PR

---

## 4. Pack 요약 (복붙 위치)

| Pack | Surface | 프롬프트 위치 |
|------|---------|---------------|
| A supplement | `.km-ask-*` tokens | `prompts/...prompt_v1.md` § Pack A 보강 |
| E | `no1kmedi.com/ask` | 동 파일 § Pack E |
| F | `clinic.../clinician` | 동 파일 § Pack F + `prompts/paste_chart_...v2_surface.md` |
| G | `jema-ai.com/hub` clinical | 동 파일 § Pack G |

전역 Pack A→D→B→C: `ssot/jemaai_antigravity_design_prompt_packs_v1_latest.md`

---

## 5. Hand-off 체크리스트

| 단계 | 설명 | 담당 | 상태 |
|------|------|------|------|
| 1 | ZIP 빌드 (`Build-KmHanMedicineUiUxHandoffZip_v1.ps1`) | Cursor | ☑ 2026-07-05 · `reports/km_han_medicine_ui_ux_v1.zip` (28711 B, 11 files) |
| 2 | 번들 준비 (`projects/km_han_medicine_ui_ux/` — repo 내 동기화 완료; 외부 수신 시 ZIP 압축 해제) | Cursor | ☑ |
| 3 | `README.md`·`SETUP.md` 검토 | 지휘관 | ☐ |
| 4 | Figma/HTML mock → `mocks/` | Antigravity | ☑ 2026-07-05 (HTML wireframes) |
| 5 | Pack A supplement → E → F → G mock 검증 | 지휘관 | ☐ |
| 6 | `cursor/MERGE_CHECKLIST.md` — CSS·presentational TSX merge | Cursor | ☑ Pack E/F/G CSS+TSX (local build exit 0) |
| 7 | Gate 테스트 (merge 후 재실행) | Cursor | ☑ baseline · deploy 후 live UI 재확인 |
| 8 | PR · Merge · Deploy | 지휘관 | ☐ |

---

## 6. 금지 항목 (Antigravity · mock 단계)

- 체질 확정 UI, 함억/두견→처방 트리거
- Track A KPI, live trading copy
- Hub cream/gold ↔ clinician dark 팔레트 무단 혼합
- TSX logic, API routes, `public-copy.json` 법무 문구

---

## 7. 첨부 SSOT (repo canonical)

| 파일 | 경로 |
|------|------|
| DTCG tokens | `docs/final/artifacts/jemaai_dtcg_tokens_proposed_v1.dtcg.json` |
| Design seed | `docs/final/artifacts/jemaai_design_reference_seed_antigravity_v1.json` |
| Concept stack | `docs/final/artifacts/mkm_ai_han_medicine_concept_stack_v1_latest.json` |
| Paste Chart surface | `reports/paste_chart_antigravity_prompt_v2_surface.md` |
| Antigravity pack index | `docs/final/artifacts/jemaai_antigravity_design_prompt_packs_v1_latest.md` |

번들 내 복사본: `projects/km_han_medicine_ui_ux/ssot/` · `prompts/`

> **주의:** `c:\workspace\artifacts\` 는 SSOT가 아님 — 사용하지 않음.

---

## 8. Cursor merge gate (merge 후)

```text
py scripts/probe_no1kmedi_national_km_ask_live_v1.py
py scripts/probe_clinician_canon_cite_live_v1.py
py -m pytest tests/test_no1kmedi_hub_clinical_p2_v1.py -q
```

Deploy: `powershell -File scripts\Deploy-No1kmediDestinyTarball_v1.ps1` (local build exit 0 후)

## 9. Gate baseline (pre-merge · 2026-07-05)

| Gate | Result |
|------|--------|
| `probe_no1kmedi_national_km_ask_live_v1.py` | `all_ok: true` |
| `probe_clinician_canon_cite_live_v1.py` | `all_ok: true` |
| `test_no1kmedi_hub_clinical_p2_v1.py` | 4 passed |

Merge 후 동일 3종 재실행 필수.
