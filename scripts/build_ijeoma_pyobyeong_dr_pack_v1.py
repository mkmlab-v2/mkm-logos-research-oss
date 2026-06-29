#!/usr/bin/env python3
"""Build IJEOMA pyobyeong / byeongjeung-yakri deep-research pack (B-track, worktree).

Tier 1: deterministic LIT_REVIEW + insight cards from workspace read-only pins.
Does not write C:\\workspace *_latest.json.

  py scripts/build_ijeoma_pyobyeong_dr_pack_v1.py
  py scripts/build_ijeoma_pyobyeong_dr_pack_v1.py --workspace-root C:/workspace
"""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "sasang-head-btrack"
RESEARCH = EXP / "research"
ART = EXP / "artifacts"

DEFAULT_WS = Path(r"C:\workspace")

CANON_REL = Path("docs/sasang-origin/정교동의수세보원원문.txt")
CROSS_REF_REL = Path("docs/final/artifacts/SASANG_CROSS_REF_DRAFT.json")
TOP10_REL = Path("docs/research/raw/SASANG_PYOBYEONG_TOP10_NL_PROXY_2026-06-24.md")
CONTRACT_REL = Path("docs/final/artifacts/SASANG_DYNAMICS_V1_CONTRACT.json")
QUERY_SET_REL = Path("experiments/sasang-head-btrack/research/ijeoma_pyobyeong_query_set_v1.json")
TIER0_REL = Path(
    "experiments/sasang-head-btrack/research/raw/PYOBYEONG_SASIM_SINMUL_DR_TIER0_20260629.md"
)

OUT_MANIFEST = ART / "ijeoma_pyobyeong_dr_pack_v1_latest.json"
OUT_CARDS = ART / "ijeoma_pyobyeong_insight_cards_v1_latest.json"
OUT_CARDS_ABLATION = ART / "ijeoma_pyobyeong_insight_cards_v1_ablation_latest.json"
OUT_LIT = RESEARCH / "IJEOMA_PYOBYEONG_BYEONGJEUNG_LIT_REVIEW_v1.md"
PACK_VERSION = "1.1.0"
CARDS_VERSION = "1.1.0"

PINNED_SECONDARY_V1: list[dict[str, str]] = [
    {
        "source_id": "SRC-OAK-ULGWANG",
        "title_ko": "소음인체질병증 임상진료지침: 울광병",
        "tier": "SECONDARY",
        "pin_kind": "oak_repository",
    },
    {
        "source_id": "SRC-KCI-SOYANG-SANGPUNG",
        "title_ko": "소양인체질병증 임상진료지침: 소양상풍병",
        "tier": "SECONDARY",
        "pin_kind": "kci_journal",
    },
    {
        "source_id": "SRC-KCI-SOYANG-MANGEUM",
        "title_ko": "소양인 망음병 CPG",
        "tier": "SECONDARY",
        "pin_kind": "kci_journal",
    },
    {
        "source_id": "SRC-ENCYK-MANGYANG",
        "title_ko": "망양병 (한국민족문화대백과)",
        "tier": "SECONDARY",
        "pin_kind": "encykorea",
    },
    {
        "source_id": "SRC-ENCYK-ULGWANG",
        "title_ko": "울광병 (한국민족문화대백과)",
        "tier": "SECONDARY",
        "pin_kind": "encykorea",
    },
    {
        "source_id": "SRC-KCI-PIYUE",
        "title_ko": "『동의수세보원』脾約에 관하여",
        "tier": "SECONDARY",
        "pin_kind": "kci_journal",
    },
    {
        "source_id": "SRC-TOP10-Lee-Song",
        "title_ko": "SciSpace TOP10 #1 표리병증 역사 (Lee & Song)",
        "tier": "SECONDARY",
        "pin_kind": "scispace_proxy",
    },
]

TIER_C_EXCLUDED = [
    "ko.wikipedia.org",
    "namu.wiki",
    "m.cafe.daum.net",
    "buya.kr",
    "mkhealth.co.kr",
    "egangdong.kr",
    "imaeil.com",
]

CANON_ANCHORS: list[dict[str, Any]] = [
    {
        "anchor_id": "CANON-01",
        "line": 397,
        "pattern": "表裏",
        "label_ko": "腹背表裏·三陰三陽 변증",
        "tier": "FACT",
    },
    {
        "anchor_id": "CANON-02",
        "line_start": 438,
        "line_end": 446,
        "pattern": "表熱病論",
        "label_ko": "少陰人 腎受熱 表熱病論",
        "tier": "FACT",
    },
    {
        "anchor_id": "CANON-03",
        "line_start": 1269,
        "line_end": 1273,
        "pattern": "表寒病論",
        "label_ko": "少陽人 脾受寒 表寒病論",
        "tier": "FACT",
    },
    {
        "anchor_id": "CANON-04",
        "line": 1328,
        "pattern": "甘遂",
        "label_ko": "表寒病 甘遂 vs 裡熱病 石膏",
        "tier": "FACT",
    },
    {
        "anchor_id": "CANON-05",
        "line_start": 742,
        "line_end": 743,
        "pattern": "表裏俱病",
        "label_ko": "少陰·太陰 表裏俱病 vs 裡病表不病",
        "tier": "FACT",
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_text(path: Path) -> str:
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8", errors="replace")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _line_at(lines: list[str], n: int) -> str:
    if 1 <= n <= len(lines):
        return lines[n - 1].strip()
    return ""


def _slice_lines(lines: list[str], start: int, end: int) -> list[str]:
    lo = max(1, start)
    hi = min(len(lines), end)
    return [lines[i - 1].strip() for i in range(lo, hi + 1) if lines[i - 1].strip()]


def _extract_canon_anchors(canon_path: Path) -> list[dict[str, Any]]:
    text = _read_text(canon_path)
    if not text:
        return []
    lines = text.splitlines()
    out: list[dict[str, Any]] = []
    for spec in CANON_ANCHORS:
        if "line_start" in spec:
            excerpt = _slice_lines(lines, int(spec["line_start"]), int(spec["line_end"]))
            line_ref = f"{spec['line_start']}-{spec['line_end']}"
        else:
            excerpt = [_line_at(lines, int(spec["line"]))]
            line_ref = str(spec["line"])
        joined = " ".join(excerpt)
        if spec["pattern"] not in joined and spec["pattern"] not in text:
            continue
        out.append(
            {
                "anchor_id": spec["anchor_id"],
                "tier": spec["tier"],
                "label_ko": spec["label_ko"],
                "source_path": str(canon_path).replace("\\", "/"),
                "line_ref": line_ref,
                "excerpt_ko": joined[:600],
            }
        )
    return out


def _cross_ref_pyobyeong_rows(cross_ref: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for entry in cross_ref.get("entries") or []:
        if not isinstance(entry, dict):
            continue
        blob = json.dumps(entry, ensure_ascii=False)
        if not re.search(r"표리|表裡|표한|表寒|表熱|表裡", blob):
            continue
        rows.append(
            {
                "entry_id": entry.get("entry_id"),
                "section_key": entry.get("section_key"),
                "satellite_ref": entry.get("satellite_ref"),
                "chunk_id": entry.get("chunk_id"),
                "line_start": entry.get("line_start"),
                "line_end": entry.get("line_end"),
                "rationale": entry.get("rationale"),
                "tier": "HYPO",
            }
        )
    return rows[:24]


def _build_orthogonal_matrix_hypo_v1() -> dict[str, Any]:
    """CPG-informed 2D matrix — advisory interpretive_notes only; not clinical SSOT."""
    return {
        "schema": "ijeoma_pyobyeong_orthogonal_matrix_hypo_v1",
        "version": "1.0.0",
        "tier": "SECONDARY",
        "axes": {
            "stage": ["cho", "jung", "mal"],
            "exposure": ["pyo", "ri"],
        },
        "forbidden": "linear_fusion_of_stage_and_exposure",
        "rows": [
            {
                "constitution_id": "soeum_in",
                "branch_id": "ulgwang",
                "label_ko": "소음인 울광병",
                "cpg_pin": "SRC-OAK-ULGWANG",
                "stage_notes_ko": {
                    "cho": "배표 통증·오한·신열·무한",
                    "jung": "오한 소실·신열 심화·대변비조",
                    "mal": "조열·광언·미천직시·집연한출",
                },
            },
            {
                "constitution_id": "soeum_in",
                "branch_id": "mangyang",
                "label_ko": "소음인 망양병",
                "cpg_pin": "SRC-ENCYK-MANGYANG",
                "stage_notes_ko": {
                    "cho": "발열·오한·자한·소변 청리",
                    "jung": "오한 없음·오열·자한·소변 자리",
                    "mal": "발열·오한·집연한출·소변적삽",
                },
                "edition_note_ko": "[SECONDARY] 갑오→신축: 위중도 지표 땀→소변 청리/적삽 (원전 행 pin 전 UNVERIFIED)",
            },
            {
                "constitution_id": "soyang_in",
                "branch_id": "sangpung",
                "label_ko": "소양인 소양상풍병",
                "cpg_pin": "SRC-KCI-SOYANG-SANGPUNG",
                "stage_notes_ko": {
                    "cho": "표한·외감 초기",
                    "jung": "외한포리열·결흉 초입",
                    "mal": "결흉조갈섬어증",
                },
            },
            {
                "constitution_id": "soyang_in",
                "branch_id": "mangeum",
                "label_ko": "소양인 망음병",
                "cpg_pin": "SRC-KCI-SOYANG-MANGEUM",
                "stage_notes_ko": {
                    "cho": "대장한기·하복통·설사",
                    "jung": "신국음기 손상·건망·불안",
                    "mal": "신한복통망음우증",
                },
            },
        ],
        "disclaimer_ko": "CPG·백과 요약 — interpretive_notes_ko·human_only. 처방·CDSS·Track A 금지.",
    }


def _build_insight_cards(
    canon_anchors: list[dict[str, Any]],
    cross_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    cards: list[dict[str, Any]] = [
        {
            "card_id": "IC-01",
            "title_ko": "표리는 부위 라벨이 아니라 노출·깊이 축",
            "insight_ko": (
                "동의수세보원은 腹背表裏·三陰三陽 변증을 경락 미시추구 없이 읽는다. "
                "2차 문헌(TOP10 #1)은 외감을 환경·감각, 내상을 감정·대인으로 요약한다. "
                "MKM에서는 사심신物(事心身物)과 병치하되 동일식 합선(E1)은 금지."
            ),
            "tier": "HYPO",
            "axes": ["pyobyeong", "byeongjeung_yakri", "sasim_sinmul"],
            "reading_order_hint": "금화(외곽) → 보명(어휘) → 본 카드 → persona 12셀 → stress/stage",
            "evidence_refs": [
                {"kind": "canon_anchor", "ref": "CANON-01"},
                {"kind": "secondary", "ref": "docs/research/raw/SASANG_PYOBYEONG_TOP10_NL_PROXY_2026-06-24.md#1"},
            ],
            "forbidden_merge_note_ko": "표리 축만으로 체질·처방·실매매 확정 금지.",
        },
        {
            "card_id": "IC-02",
            "title_ko": "체질마다 표리 문법이 다름 — 소음 표열 vs 소양 표한",
            "insight_ko": (
                "少陰人 腎受熱 表熱病論과 少陽人 脾受寒 表寒病論은 서두 제목부터 대칭이 아니다. "
                "cross_ref 청크는 소음 신수열·표열, 소양 비수한·표한, 태음 위완수한·표한을 분리 보관한다. "
                "한 체질의 표리 규칙을 타 체질 persona cell에 복사하면 FAIL."
            ),
            "tier": "FACT",
            "axes": ["pyobyeong", "four_constitutions"],
            "evidence_refs": [
                {"kind": "canon_anchor", "ref": "CANON-02"},
                {"kind": "canon_anchor", "ref": "CANON-03"},
                {"kind": "cross_ref", "ref": "SASANG_CROSS_REF_DRAFT entries (표한/表熱 서두)"},
            ],
            "forbidden_merge_note_ko": "12셀 active_cell_id만으로 표리 판정 금지.",
        },
        {
            "card_id": "IC-03",
            "title_ko": "병증약리 핵심 = 표리 약성 오용 경고",
            "insight_ko": (
                "이마는 表寒病에 甘遂, 裡熱病에 石膏처럼 표·리별 약성을 명시한다. "
                "cross_ref에는 표리 불분·표리 병겸·감수·석고 표리약 대조·화열 급변 경계 청크가 있다. "
                "엔지니어링 번역: force_hold·veto는 『추격·오용 금지』 전술 leg이지 처방 엔진이 아님."
            ),
            "tier": "HYPO",
            "axes": ["byeongjeung_yakri", "pyobyeong"],
            "evidence_refs": [
                {"kind": "canon_anchor", "ref": "CANON-04"},
                {"kind": "cross_ref", "ref": "chunks 00005, 00014, 00019, 00046"},
            ],
            "forbidden_merge_note_ko": "symptom_weights·market proxy table과 임상 병증약리 동일시 금지.",
        },
        {
            "card_id": "IC-04",
            "title_ko": "初中末 × 표리 = 직교 2D 읽기",
            "insight_ko": (
                "contract pathology_stage(cho|jung|mal|anjeong)는 stress 밴드에서 유도. "
                "표리는 감염·노출 vs 내상 축. 같은 중증이라도 中證+表病과 中證+裡病은 다른 문헌 맥락. "
                "persona grid 12셀은 톤·라우팅 메타이지 표리 축 대체가 아님."
            ),
            "tier": "FACT",
            "axes": ["byeongjeung_yakri", "persona_grid", "pathology_stage"],
            "evidence_refs": [
                {"kind": "contract", "ref": "SASANG_DYNAMICS_V1_CONTRACT.json formulas_v1.pathology_stage"},
                {"kind": "cross_ref", "ref": "망양·망음 예방 청크 00035"},
            ],
            "forbidden_merge_note_ko": "stress 단일 스코어로 표리·初中末 선형 합성 금지.",
        },
        {
            "card_id": "IC-05",
            "title_ko": "張仲景 인용 = 사상 四象 재매핑 레이어",
            "insight_ko": (
                "원전은 傷寒論 구절을 인용한 뒤 論曰로 少陰人/少陽人 병증으로 재해석한다. "
                "이는 동의보감식 분류를 그대로 따르지 않겠다는 경계. RAG는 인용사(仲景·龔信)별 격벽 유지 필요."
            ),
            "tier": "FACT",
            "axes": ["pyobyeong", "zhang_zhongjing_bridge"],
            "evidence_refs": [
                {"kind": "canon_anchor", "ref": "CANON-02"},
                {"kind": "canon_anchor", "ref": "CANON-05"},
            ],
            "forbidden_merge_note_ko": "TCM 태양병 라벨을 사상 체질과 1:1 동일시 금지.",
        },
        {
            "card_id": "IC-06",
            "title_ko": "판본·시간에 따른 병증약리 진화",
            "insight_ko": (
                "2차 논문(TOP10 #2, #9)은 갑오본↔신축본에서 亡陰證·복통설사 등 분류가 정제됨을 서술. "
                "레포 primary 한자 격치고·천유초는 미입수 — 판본 단정은 [UNVERIFIED] until canon acquired."
            ),
            "tier": "SECONDARY",
            "axes": ["byeongjeung_yakri", "edition_drift"],
            "evidence_refs": [
                {"kind": "secondary", "ref": "SASANG_PYOBYEONG_TOP10 #2"},
                {"kind": "secondary", "ref": "SASANG_PYOBYEONG_TOP10 #9"},
            ],
            "forbidden_merge_note_ko": "판본 차이를 Track A·임상 SSOT로 승격 금지.",
        },
        {
            "card_id": "IC-07",
            "title_ko": "시장 byeongjeung proxy ≠ 임상 표리병증",
            "insight_ko": (
                "sasang_byeongjeung_yakri_proxy_table_v1은 VIX·volume 은유로 sweating/chills 등을 만든 "
                "B-track Step-1 frozen table이다. 본 딥리서치 팩의 표리·병증약리 통찰과 인과 단정·합선 금지."
            ),
            "tier": "FACT",
            "axes": ["track_wall"],
            "evidence_refs": [
                {"kind": "artifact", "ref": "docs/final/artifacts/sasang_byeongjeung_yakri_proxy_table_v1_latest.json"},
            ],
            "forbidden_merge_note_ko": "step12 leakage pass를 임상 검증으로 읽지 말 것.",
        },
        {
            "card_id": "IC-08",
            "title_ko": "사심신물 ↔ 표리 노출 축 (격치고 브리지)",
            "insight_ko": (
                "DR Tier0: 表病≈事·身(외부·감각·환경 노출), 裏病≈心·物(정서·대인·내적 집착). "
                "격치고 partial(SP-01 物宅身也…)와 정합 가능하나 primary 한자 미입수 — [HYPO] 교육·interpretive_notes만. "
                "S-L-K-M·regime_map·stress 식과 동일식 합선(E1/E2) 금지."
            ),
            "tier": "HYPO",
            "axes": ["sasim_sinmul", "pyobyeong", "worldview_annotation"],
            "evidence_refs": [
                {"kind": "tier0_ingest", "ref": TIER0_REL.as_posix()},
                {"kind": "partial_canon", "ref": "IJEOMA_SECONDARY_PROXY_v1 SP-01"},
                {"kind": "canon_anchor", "ref": "CANON-01"},
            ],
            "forbidden_merge_note_ko": "사심신물 브리지를 체질 라벨·처방·CDSS 입력으로 승격 금지.",
        },
        {
            "card_id": "IC-09",
            "title_ko": "CPG 직교 2D 매트릭스 (울광/망양·상풍/망음 × 초중말)",
            "insight_ko": (
                "Commander DR의 2D 표를 orthogonal_matrix_hypo_v1로 구조화. "
                "stage 축=contract pathology_stage(cho|jung|mal); exposure 축=표·리·분기(울광|망양 등). "
                "Advisory Only — pinned SECONDARY(KCI/OAK/encyk)만; Tier C 출처 미사용."
            ),
            "tier": "SECONDARY",
            "axes": ["pyobyeong", "byeongjeung_yakri", "persona_grid", "cpg_matrix"],
            "evidence_refs": [
                {"kind": "matrix", "ref": "orthogonal_matrix_hypo_v1"},
                {"kind": "pinned_secondary", "ref": "pinned_secondary_v1"},
            ],
            "forbidden_merge_note_ko": "매트릭스 셀→처방·active_cell_id 자동 매핑 금지.",
        },
    ]
    ortho = _build_orthogonal_matrix_hypo_v1()
    return {
        "schema": "ijeoma_pyobyeong_insight_cards_v1",
        "version": CARDS_VERSION,
        "generated_at_utc": _utc(),
        "rail": "B_TRACK",
        "research_only": True,
        "send_gate": "HOLD",
        "decision_authority": "human_only",
        "advisory_only": True,
        "tier0_ingest": str((ROOT / TIER0_REL).as_posix()),
        "pinned_secondary_v1": PINNED_SECONDARY_V1,
        "tier_c_excluded_hosts": TIER_C_EXCLUDED,
        "orthogonal_matrix_hypo_v1": ortho,
        "canon_anchors": canon_anchors,
        "cross_ref_pyobyeong_sample_count": len(cross_rows),
        "cards": cards,
    }


def _build_lit_review(
    ws: Path,
    cards_doc: dict[str, Any],
    canon_anchors: list[dict[str, Any]],
    cross_rows: list[dict[str, Any]],
    query_doc: dict[str, Any],
) -> str:
    ortho = cards_doc.get("orthogonal_matrix_hypo_v1") or {}
    lines = [
        "# IJEOMA · 표리병증·병증약리 LIT_REVIEW v1.1",
        "",
        f"**generated_at_utc:** {_utc()}",
        f"**pack_version:** {PACK_VERSION}",
        "**rail:** B_TRACK · **research_only** · `send_gate: HOLD`",
        "**decision_authority:** human_only · **advisory_only** — CDSS·자동 처방·Track A 아님",
        "",
        "## Fact-Lock",
        "",
        "- 임상·처방·Track A·실매매 단정 금지.",
        "- `sasang_byeongjeung_yakri_proxy_table` = 시장 B-track 은유; **임상 표리 SSOT 아님**.",
        "- IJEOMA_BTRACK ≠ LENS_SASANG 노트북 합침.",
        "- E1: 단일 TOE·dx/dt·우주통일·임상 예측 한 덩어리 금지.",
        "- E4: CDSS·디지털 헬스 자동 승격 금지 — Veto/Hold는 오용 차단 은유만.",
        "- Tier0: `research/raw/PYOBYEONG_SASIM_SINMUL_DR_TIER0_20260629.md` (위키·카페 등 Tier C 미인용).",
        "",
        "## Tier map",
        "",
        "| tier | 의미 |",
        "| --- | --- |",
        "| `[FACT]` | workspace 정본 행·contract 수식·격벽 아티팩트 |",
        "| `[SECONDARY]` | SciSpace TOP10·논문 proxy |",
        "| `[HYPO]` | MKM 해석 카드·cross_ref rationale |",
        "",
        "## Canon anchors (workspace 정교본)",
        "",
    ]
    for a in canon_anchors:
        lines.append(f"### {a['anchor_id']} · {a['label_ko']} `[{a['tier']}]`")
        lines.append(f"- **lines:** {a['line_ref']}")
        lines.append(f"- **excerpt:** {a['excerpt_ko'][:400]}…" if len(a["excerpt_ko"]) > 400 else f"- **excerpt:** {a['excerpt_ko']}")
        lines.append("")

    lines.extend(
        [
            "## Insight cards (요약)",
            "",
        ]
    )
    for card in cards_doc.get("cards") or []:
        lines.append(f"### {card['card_id']} · {card['title_ko']} `[{card['tier']}]`")
        lines.append(card["insight_ko"])
        lines.append("")

    lines.extend(["## Pinned secondary (DR 출처 청소)", ""])
    for src in cards_doc.get("pinned_secondary_v1") or []:
        lines.append(f"- **{src.get('source_id')}** · {src.get('title_ko')} `[{src.get('tier')}]`")
    lines.append("")
    lines.append("## Orthogonal 2D matrix (IC-09) `[SECONDARY]`")
    lines.append("")
    for row in ortho.get("rows") or []:
        lines.append(f"- **{row.get('label_ko')}** · pin `{row.get('cpg_pin')}`")
    lines.append("")

    lines.extend(
        [
            "## Cross-ref 표리 샘플 (HYPO)",
            "",
            f"총 {len(cross_rows)}행 샘플 — `SASANG_CROSS_REF_DRAFT.json`",
            "",
        ]
    )
    for row in cross_rows[:8]:
        lines.append(f"- **{row.get('entry_id')}** · {row.get('satellite_ref')}")

    lines.extend(
        [
            "",
            "## NL query set (PBQ01–PBQ08)",
            "",
            "배치: `py scripts/run_ijeoma_pyobyeong_query_set_v1.py`",
            "",
        ]
    )
    for q in query_doc.get("questions") or []:
        lines.append(f"- **{q.get('query_id')}** ({q.get('topic')}): {q.get('question_ko')}")

    lines.extend(
        [
            "",
            "## Reproduce",
            "",
            "```powershell",
            "cd C:\\mkm-sasang-ablation",
            "py scripts/build_ijeoma_pyobyeong_dr_pack_v1.py",
            "py -m pytest tests/test_ijeoma_pyobyeong_dr_pack_v1.py -q",
            "py scripts/run_ijeoma_pyobyeong_query_set_v1.py --dry-run",
            "```",
            "",
        ]
    )
    return "\n".join(lines) + "\n"


def build_pack(workspace_root: Path) -> dict[str, Any]:
    canon_path = workspace_root / CANON_REL
    cross_ref = _read_json(workspace_root / CROSS_REF_REL)
    contract = _read_json(workspace_root / CONTRACT_REL)
    query_doc = _read_json(ROOT / QUERY_SET_REL if (ROOT / QUERY_SET_REL).is_file() else RESEARCH / "ijeoma_pyobyeong_query_set_v1.json")
    if not query_doc.get("questions"):
        alt = ROOT / "docs/research/ijeoma_pyobyeong_query_set_v1.json"
        if alt.is_file():
            query_doc = _read_json(alt)

    canon_anchors = _extract_canon_anchors(canon_path)
    cross_rows = _cross_ref_pyobyeong_rows(cross_ref)
    cards_doc = _build_insight_cards(canon_anchors, cross_rows)
    lit_md = _build_lit_review(workspace_root, cards_doc, canon_anchors, cross_rows, query_doc)

    RESEARCH.mkdir(parents=True, exist_ok=True)
    ART.mkdir(parents=True, exist_ok=True)
    OUT_LIT.write_text(lit_md, encoding="utf-8")
    cards_json = json.dumps(cards_doc, ensure_ascii=False, indent=2) + "\n"
    OUT_CARDS.write_text(cards_json, encoding="utf-8")
    OUT_CARDS_ABLATION.write_text(cards_json, encoding="utf-8")

    manifest = {
        "schema": "ijeoma_pyobyeong_dr_pack_v1",
        "version": PACK_VERSION,
        "generated_at_utc": _utc(),
        "rail": "B_TRACK",
        "research_only": True,
        "send_gate": "HOLD",
        "workspace_root": str(workspace_root).replace("\\", "/"),
        "inputs": {
            "canon": str(canon_path).replace("\\", "/"),
            "canon_present": canon_path.is_file(),
            "cross_ref": str((workspace_root / CROSS_REF_REL)).replace("\\", "/"),
            "top10_proxy": str((workspace_root / TOP10_REL)).replace("\\", "/"),
            "contract_pathology_stage": (contract.get("formulas_v1") or {}).get("pathology_stage", {}).get("id"),
            "query_set": str((ROOT / QUERY_SET_REL)).replace("\\", "/"),
            "tier0_ingest": str((ROOT / TIER0_REL)).replace("\\", "/"),
        },
        "outputs": {
            "lit_review_md": str(OUT_LIT.relative_to(ROOT)).replace("\\", "/"),
            "insight_cards_json": str(OUT_CARDS.relative_to(ROOT)).replace("\\", "/"),
            "insight_cards_ablation_json": str(OUT_CARDS_ABLATION.relative_to(ROOT)).replace("\\", "/"),
            "manifest_json": str(OUT_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        },
        "counts": {
            "canon_anchors": len(canon_anchors),
            "insight_cards": len(cards_doc.get("cards") or []),
            "cross_ref_pyobyeong_rows": len(cross_rows),
            "query_count": len(query_doc.get("questions") or []),
        },
        "nl_batch_pending": True,
        "reproduce": [
            "py scripts/build_ijeoma_pyobyeong_dr_pack_v1.py",
            "py scripts/run_ijeoma_pyobyeong_query_set_v1.py",
        ],
    }
    OUT_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace-root", type=Path, default=DEFAULT_WS)
    args = parser.parse_args()
    manifest = build_pack(args.workspace_root.resolve())
    print(json.dumps({"ok": True, "manifest": str(OUT_MANIFEST), "counts": manifest["counts"]}, ensure_ascii=False))
    if not manifest["inputs"]["canon_present"]:
        print("WARN: canon missing — anchors may be empty", file=__import__("sys").stderr)
        return 1
    if manifest["counts"]["canon_anchors"] < 3:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
