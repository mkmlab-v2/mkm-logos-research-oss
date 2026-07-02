# Antigravity Pack L-Ask v1 – Commander Answers (5 Q&A)

**1. Figma 전달 방식**
- **1차**: Figma share link (view or dev mode) – includes Frames A-D at 390 / 768 / 1440 breakpoints and the full component set.
- **2차**: ZIP export `docs/final/artifacts/logos_ask_figma_v1.zip` – contains PNG/SVG exports of every frame plus a `README.md` that maps each Figma frame to the corresponding CSS class name.
- *이미지만 ZIP 단독은 허용되지 않으며, Component spec(D2)과 class 대조를 위해 반드시 Figma 링크가 필요합니다.*

**2. 추가 색상·토큰 제약**
| 구분 | hex / 역할 | 비고 |
|------|-----------|------|
| **금지 (hero/CTA)** | `#5b8cff` marketing blue | `preset-stripe-linear` – hub 전용 |
| **금지** | `rgba(91,140,255,…)` enterprise glow | `/enterprise` chrome |
| **금지** | `#191919` hub dark | `/hub` 전용 |
| **금지** | crypto/Web3 gradient, 과다 glassmorphism | Pack A 제약 |
| **허용 (Ask surface)** | cream `#faf7f2`, teal `#2d7a68`, gold `#c5a057`, ink `#292524` | Scriptorium mockup SSOT |
| **허용 (functional)** | error `#b91c1c` / `#fef2f2`, muted `#57534e` | quota / error UI |

- 신규 토큰은 `color.logos.ask.*` 네임스페이스에 배치하고, 기존 `--space-*`, `--radius-*`, `--text-*` 변수를 **재사용**합니다.
- `--accent` 를 hub와 합치지 말고, Ask 전용 `--accent-ask` 등 별도 변수 사용.

**3. 다크 모드**
- **P0 / P1**: 라이트 전용 (Frame C Done 1440 + 390, Frame A/B/D light) – 다크 모드 **필수 아님**.
- **P2 (optional)**: `optional-dark-explore` 라벨을 붙인 다크 프레임만 Figma에 포함. 프로덕션 CSS/DTCG 에는 적용되지 않음.

**4. 이미지·아이콘**
- 현재 레포에 존재하는 SVG/텍스트 badge 를 그대로 재사용합니다.
- **Graph path / mindmap**: `PathMindmapSvgPanel` – 패널 chrome (border, padding, toggle)만 스타일링.
- **Viz toggle**: 텍스트 버튼 `.lr-ask-graph-viz-btn` – 아이콘 추가 **금지** (P0). P1 이후 필요 시 Lucide stroke 16px teal 1종만 사용.
- **Citation lock chips**, `[HYPO]` / `[NON_GATING]` badge: 텍스트 badge만 유지.
- **Handoff badge**: 레이아웃 정리만 진행.

**5. 버전 관리**
- **CSS patch**: `globals.css.diff` 대신 `logos_ask_scoped_css_patch_v1.diff` 파일명 사용 (전역 CSS 전체 커밋 금지).
- **ASK_UI_REV**: 최초 `20260702c` → Antigravity merge 1회당 suffix (`d`, `e`…) 증가.
  - 파일 `LogosResearchAskClient.tsx`에 `data-logos-ask-ui-rev={ASK_UI_REV}` 속성 유지.
- **DTCG JSON**: 기존 파일 전체 교체 OK, 단 `antigravity_proposed_*` 슬롯만 채움.
- **Artifact 파일**: 레이아웃에 큰 변화가 있으면 파일명에 `_v2` 등 버전 suffix 추가.
- **Git commit**: Cursor가 merge 후 1 commit만 생성 – diff·artifact만 포함.

---
**핵심 요약**
- Figma 링크 + ZIP 백업
- Ask 전용 색상만 사용, 금지 색상 절대 포함 금지
- 다크 모드는 옵션 (P2)만
- 기존 SVG 재사용, 아이콘 신규 제작 금지
- `ASK_UI_REV` 문자열 기반 버전 관리, 전역 CSS 전체 교체 금지

**Cursor P0 merge 대기 산출물 (Antigravity → 레포):**

| ID | 파일 |
|----|------|
| D1 | Figma link + `logos_ask_figma_v1.zip` |
| D2 | `logos_ask_component_spec_v1.md` |
| D3 | `logos_ask_scoped_css_patch_v1.diff` |
| D4 | `jemaai_dtcg_tokens_proposed_v1.dtcg.json` (ask slots) |
| D5 | `logos_ask_rationale_ko.md` (선택) |

**Merge 후 Cursor 검증:**

```powershell
cd projects/no1kmedi
npm run check:design-tokens
npm run check:marketing-copy
npm run smoke:logos-inquiry-ask
npm run smoke:logos-inquiry-ask-playwright
npm run verify:logos-ask-graph-live
py ../../scripts/check_jemaai_dtcg_proposed_v1.py
```

**P0 Cursor merge (2026-07-02):** `ASK_UI_REV=20260702c` · artifacts D2–D4 applied · Figma link deferred (`logos_ask_figma_link.md`).
