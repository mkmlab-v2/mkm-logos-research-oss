# AI-Logos Research Bibliography (B-Track Only)

**작성일**: 2026-03-29  
**역할**: NotebookLM **B(통찰·연구)** 전용. **A·본선 OOF·실매매 로직과 무단 합선 금지** (`docs/NotebookLM_sources_manifest.md`).

**요약 (3문장)**: 본 문서는 arXiv·Kaggle 등 **확인 가능한 공개 URL**만 서지로 고정한다. 마케팅 명칭·미검증 수치(예: “100년”, “Project Enoch”)는 **TBD**로 분리한다. 승격은 `MYEONGNI_FUSION_DECISION` 등 스키마에 **검증 후** 필드 추가로만 수행한다.

---

## 태그 규칙

| 접두어 | 의미 |
|--------|------|
| `[PAPER]` | 학술 논문·프리프린트 |
| `[KAGGLE]` | Kaggle 대회·노트북(기술·벤치마크 참고) |
| `[TECH]` | 기술 문서·튜토리얼(본 서지에 미포함 시 별도 추가) |

---

## Confirmed (arXiv·페이지 직접 확인, 2026-03-29)

### [PAPER] LeWorldModel (JEPA / world model)

- **Title**: LeWorldModel: Stable End-to-End Joint-Embedding Predictive Architecture from Pixels  
- **arXiv**: https://arxiv.org/abs/2603.19312  
- **PDF**: https://arxiv.org/pdf/2603.19312  
- **Authors**: Lucas Maes, Quentin Le Lidec, Damien Scieur, Yann LeCun, Randall Balestriero  
- **Note (abstract)**: JEPA 계열; ~15M 파라미터, 계획(planning) 속도 관련 벤치마크 서술은 논문 본문·표를 따른다(채팅에서 수치 단정 금지).

### [PAPER] Dead Sea Scrolls — ink/parchment segmentation (multispectral)

- **Title**: Segmentation of Ink and Parchment in Dead Sea Scroll Fragments  
- **arXiv**: https://arxiv.org/abs/2411.10668  
- **PDF**: https://arxiv.org/pdf/2411.10668  
- **Authors**: Berat Kurar-Barakat, Nachum Dershowitz  

### [PAPER] Dead Sea Scrolls — AI writer identification (1QIsaa)

- **Title**: Artificial intelligence based writer identification generates new evidence for the unknown scribes of the Dead Sea Scrolls exemplified by the Great Isaiah Scroll (1QIsaa)  
- **arXiv**: https://arxiv.org/abs/2010.14476  
- **PDF**: https://arxiv.org/pdf/2010.14476  
- **Journal DOI (related)**: https://doi.org/10.1371/journal.pone.0249769 (PLoS ONE; arXiv 페이지에 기재됨)

### [KAGGLE] Vesuvius Challenge — Ink Detection

- **Competition**: https://www.kaggle.com/competitions/vesuvius-challenge-ink-detection  
- **용도**: 탄화 문서/3D·잉크 검출 파이프라인 참고(B-only).

### [KAGGLE] NLP — text regression / readability (대표 사례)

- **Competition**: https://www.kaggle.com/competitions/commonlitreadabilityprize  
- **용도**: 텍스트 난이도·회귀 태스크 우수 노트 참고(B-only).

### [PAPER] Dead Sea Scrolls — radiocarbon + AI writing-style dating (“Enoch”)

- **Title**: Dating ancient manuscripts using radiocarbon and AI-based writing style analysis  
- **arXiv**: https://arxiv.org/abs/2407.12013  
- **PDF**: https://arxiv.org/pdf/2407.12013  
- **Authors**: Mladen Popović, Maruf A. Dhali, Lambert Schomaker, Hans van der Plicht, et al.  
- **Note (abstract)**: 논문은 스타일 기반 연대 예측 모델명 **Enoch**를 명시. 검증(leave-one-out)에서 방사성탄소 연대와 비교한 **MAE 약 27.9–30.7년** 수준이 보고됨. **“±100년” 단정은 본 초록·본 서지에 없음** — 언론·채팅에서 해당 수치를 사실처럼 쓰지 말 것. 미디어의 “Project Enoch”는 동일 연구계열을 가리키는 **비공식 명칭**일 수 있으며, 서지 확정명은 위 논문·모델명 **Enoch**를 따른다.

### [TECH] Deep Past Initiative (DPI)

- **Site**: https://www.deeppast.org/  
- **Challenge (intro)**: https://www.deeppast.org/challenge/intro  
- **Note**: 고대 서판·쐐기문자 디지털화·ML 경진(Deep Past Challenge) 등 공식 설명은 상기 페이지 기준. 데이터셋 버전·라이선스는 Kaggle **Dataset** 탭·대회 규칙을 매 실행 전 확인(B-only).

### [KAGGLE] Deep Past Challenge — Akkadian → English

- **Competition**: https://www.kaggle.com/competitions/deep-past-initiative-machine-translation  
- **용도**: Deep Past Initiative 공개 Kaggle 경진(기계번역) 벤치마크 참고(B-only). 연도·데이터 스냅샷은 해당 페이지 기준.

---

## TBD / Unverified (NotebookLM 답변·언론 표현 금지 — 별도 팩트체크 전)

| 주장·이름 | 상태 | 비고 |
|-----------|------|------|
| “Project Enoch” **±100년** 정확도 등 | **미확인** | **arXiv 2407.12013 초록에는 없음** — 1차 근거는 위 `[PAPER] … Enoch`만 인용 |
| Deep Past — **2026 이후 데이터셋 단일 스냅샷·라이선스 문구** | **실행 시 확인** | 공식 **대회 URL**은 상기 `[KAGGLE] Deep Past Challenge`로 고정(2026-03-29). 버전별 ZIP·규칙은 Kaggle에서 직접 확인 |

---

## 자기 파괴적 질의 (NotebookLM B, 소스 반영 후)

NotebookLM B에 위 URL이 반영된 뒤, 아래를 **통찰용**으로만 질의한다(본선 자동 트리거 금지).

1. **최신 월드 모델(JEPA·LeWorldModel류) 관점에서**, 금융 시계열·내부 “다상태(예: 16-상태)” 설계의 **일반적 취약점**(분포 이동, 인과 혼동, 검증 데이터 누수 등)은 무엇인가?  
2. 사해·고문헌 NLP(세그멘테이션·필적 식별)와 **비트코인 온체인 휴리스틱** 사이의 **비유의 한계**는 무엇인가?

---

## Next Action (지휘관 선택)

- **[A]** `notebook_get`으로 B 노트북 소스 수·제목 갱신 후 본 매니페스트 표를 한 줄 업데이트한다.  
- **[B]** TBD 항목만 별도 팩트체크 후 Confirmed 섹션에 1–2줄씩 추가한다.
