# 맥북 최적화 운영 카드 v1

**status:** operational (2026-07-09)  
**기기:** mkmlab-macbookpro · Monterey · 2014 Intel  
**원칙:** 맥 = **가벼운 병렬 스테이션** · PC = **무거운 작업·JEMA spine**  
**SSOT 상세:** `docs/final/MACBOOK_REMOTE_DEV_ENV_V1.md`

---

## 0. 결론 (한 줄)

**메인 PC가 버벅일 때 “더 어려운 작업”을 맥북으로 넘기지 말 것.**  
맥북은 **가벼운 동시 작업**만. 무거운 건 PC를 **쉬게 하거나** PC에서만 돌린다.

---

## 1. 역할 분담표

| 작업 | 어디서 | 비고 |
|------|--------|------|
| Cursor Agent · 멀티파일 · pytest · Fact-Lock · gate | **PC Cursor만** | GPU·RAM·JEMA rules |
| 대형 벤치 · Fact-Lock 번들 · 장시간 스크립트 | **PC만** | 맥으로 옮기면 **더 느림** |
| SSH로 `C:\workspace` 편집 · 가벼운 수정 | **맥 VS Code SSH** | thin surface (실행은 PC) |
| Gemini 채팅 · AI Studio 목업 | **맥 로컬 / AI Studio** | 클라우드 — 맥 CPU 거의 안 씀 |
| Safari PWA · iOS 홈화면 · 시니어 가독성 | **맥 로컬** | PC에 없는 검증 |
| 디자인 Pack 목업 HTML | **AI Studio (기본)** · Antigravity(가끔) | Antigravity는 무거움 · drop-in: `docs/final/artifacts/antigravity_mac_dropin/` · pointer `mkm_antigravity_mac_agents_v1_latest.md` |
| iOS 빌드·서명 | **맥 Xcode** (필요 시만) | 앱스토어 갈 때만 |

**동시에 쓰기:** PC Cursor **켜둔 채** + 맥 VS Code SSH / Gemini = **OK**  
**동시에 Cursor 2대:** **금지** (계정 튕김)

---

## 2. 맥북 최적화 세팅 체크리스트 (1회)

### A. 시스템 (Monterey)

| # | 항목 | 설정 |
|---|------|------|
| ☐ | 디스플레이 | 텍스트 크게 (디스플레이 → 조정) |
| ☐ | Energy | 전원 연결 시 **잠자기 방지**(작업 중) · 끝났으면 끄기 |
| ☐ | 메모리 | **Chrome 탭 최소화** · Safari는 검증용만 |
| ☐ | 동시 앱 | Antigravity + VS Code + Xcode **동시에 세 개 금지** → 하나씩 |
| ☐ | Storage | 여유 **20GB+** 유지 (앱·캐시) |

### B. AI (이미 한 것 + 권장)

| # | 항목 | 설정 |
|---|------|------|
| ☐ | Tailscale | Connected · PC `100.118.13.22` ping OK |
| ☐ | Gemini / AI Studio | API 키 OK · **채팅·목업 기본** |
| ☐ | VS Code Remote-SSH | `PRO@100.118.13.22` → `C:\workspace` (가볍 편집만) |
| ☐ | Azure BYOK | **포기해도 됨** — Gemini로 대체 |
| ☐ | Codeium | Tab만 필요하면 · 로그인 안 되면 **생략** |
| ☐ | Continue + 로컬 Ollama | **비권장** (맥 부담·품질↓) |
| ☐ | 맥 Cursor | **설치하지 않음** |

### C. 동시 프로세스 규칙

```
맥에서 동시에 켜도 되는 것:
  Tailscale + (VS Code SSH 또는 AI Studio Safari) + (선택: Figma Lite)

맥에서 같이 켜지 말 것:
  Antigravity + Xcode + VS Code + Chrome 수십 탭
```

---

## 3. PC가 버벅일 때 — 맞는지 틀린지

| 상황 | 맞는 대응 | 틀린 대응 |
|------|-----------|-----------|
| PC Cursor Agent 돌리는 중 | 맥에서 **Gemini·목업·문서·PWA 검증** | 맥에 동일 Agent·벤치 한 번 더 |
| PC pytest / Fact-Lock 중 | 맥 SSH로 **로그 보기·가벼운 문서**만 | 맥에서 같은 벤치 재실행 |
| PC GPU Ollama 사용 중 | 맥은 **Gemini**만 (클라우드) | 맥에서 Ollama+Continue |
| PC 발열·팬 풀가동 | PC **작업 큐 줄이기** · 맥은 보조 | “어려운 일”을 맥으로 이전 |

**이유:** 2014 맥북 RAM/CPU ≪ PC. 무거운 일을 옮기면 **둘 다 느려지거나 맥만 멈춤**.  
**병렬 이득**은 “어려운 일 분담”이 아니라 **가벼운 일 병행**이다.

---

## 4. 추천 하루 루틴

### PC 본선 (버벅여도 여기)

1. Cursor Agent / 레포 코딩 / gate / pytest  
2. 한 번에 **한 Agent 창** (병렬 과도 금지)

### 맥 보조 (동시)

1. Tailscale ON  
2. **AI Studio / Gemini** — 프롬프트·목업·짧은 코드 질문  
3. 또는 **VS Code SSH** — `C:\workspace`에서 **소수 파일**만 수정  
4. 디자인 검증 — Safari / iPhone 미리보기  
5. (가끔) AI Studio HTML → `mocks/`에 저장은 SSH 또는 USB

### 끝낼 때

- 맥: Antigravity/Xcode 종료 · Tailscale은 다음을 위해 둬도 됨  
- PC: 긴 잡이 돌면 **완료까지 건드리지 않기**

---

## 5. 앱별 우선순위 (가성비)

```
1순위  PC Cursor          … 전부
2순위  맥 Gemini/AI Studio … 채팅·목업 (클라우드)
3순위  맥 VS Code SSH      … 가벼운 동시 편집
4순위  맥 Antigravity      … UI 여러 장 반복 때만
5순위  맥 Xcode            … iOS 패키징만
```

---

## 6. 스모크 (세팅 확인 1분)

```bash
# 맥 터미널
ping -c 3 100.118.13.22
```

```text
# AI Studio / Gemini
오늘 날짜랑 "맥북 Gemini OK" 한 줄만 답해줘
```

```powershell
# VS Code SSH 터미널 (선택)
py scripts/athena_doctor_v1.py
```

---

## 7. 관련 파일

| 파일 | 용도 |
|------|------|
| `docs/final/MACBOOK_OPT_OPS_CARD_V1.md` | **이 카드** (최적화·역할) |
| `docs/final/MACBOOK_REMOTE_DEV_ENV_V1.md` | 상세 설치·SSH |
| `tools/gibMacOS/MAC-MINIMAL-WORKFLOW.txt` | 요약본 |
| `tools/gibMacOS/AZURE-BYOK-MAC-PROMPT.txt` | Azure (선택·포기 가능) |

---

**Revision:** 2026-07-09 — v1 · Gemini 기본 · 어려운 작업 맥 이전 금지 · PC 병행은 가벼운 일만.
