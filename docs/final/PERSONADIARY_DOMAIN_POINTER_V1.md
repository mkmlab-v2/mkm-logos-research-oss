# personadiary.com — 도메인 포인터 v1 (미확정 항목 명시)

**목적:** `personadiary.com` 을 **다른 MKM 소비자 제품(mkmlife·no1kmedi 랜딩 등)과 동일 배포·동일 API로 가정하지 않도록** 레포에 고정한다. NotebookLM·구 기획의 B2C 일기·페르소나 서술은 **참고**이며, **데이터 주거·법무는 별도 검토**다.

---

## 1) 현재 상태 (Fact-Lock)

| 항목 | 값 |
|------|-----|
| **레포 내 전용 앱 경로** | **미확정** — `projects/...` 에 고정된 트리 없음. |
| **전용 런북** | **없음** — 확정 전 **타 도메인 런북 복붙 금지**. |
| **PM2 앱 이름 / `exec cwd`** | **미확정** — 본선은 **`pm2 describe` 실측**만 신뢰. |
| **개인 일기·페르소나 데이터** | 저장 위치·암호화·해외 이전 여부는 **제품 설계·법무 확정 전** 레포 SSOT로 단정하지 않는다. |

---

## 2) 확정 전 금지 (VPS·혼선 방지)

- **mkmlife**(`mkm-life`)·**no1kmedi** 백엔드·**jemaai.cloud** 쇼룸과 **동일 DB·동일 API 키·동일 PM2 앱**이라고 가정하고 nginx/upstream 을 묶지 않는다.
- `docs/final/NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` 의 **면책·§10 배지** 문구를 personadiary UI에 **그대로 복사해 “동일 서비스”로 표시**하지 않는다 — **화면별 법무 검토** 전제.
- 기획 노트만으로 **본선 URL·웹훅·실키** 를 배포한다고 단정하지 않는다.

---

## 3) 확정 시 이 문서에 채울 항목 (체크리스트)

- [ ] Git 원격 또는 모노레포 하위 경로
- [ ] 로컬 작업 디렉터리
- [ ] PM2 이름 · `exec cwd` (실측)
- [ ] nginx `server_name` 및 정적/API 분리 여부
- [ ] 데이터 저장소(로컬 전용 / 서버 / 분리 계정) — **한 줄 SSOT**
- [ ] `MKM_DOMAIN_PORTFOLIO_POINTER_V1.md` 표 갱신

---

## 4) 교차 참조

- **mkmlife.com** 원퀘스천·단건 과금 락 — `NO1KMEDI_MKMLIFE_REPO_PATH_SSOT_2026-04-08.md` §11 — personadiary 와 **합쳐서 서술 금지** (제품이 다르면).
- **jemaai.cloud** 공개 쇼룸 — 실매매·조종실 격벽; personadiary 와 **동일 “관측 파이프”로 합선 금지** (역할이 다르면).

**개정:** 체크리스트 완료 후 v2 또는 “확정” 절 추가.
