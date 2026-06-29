"""Tests for MKM long-term memory graph ([HYPO] / B-track)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_long_term_memory_graph_lib_v1 import (  # noqa: E402
    CONCEPT_BY_ID,
    build_graph_document,
    resolve_lane_from_graph,
    route_concepts_by_query,
    score_concept_query,
    verify_graph_sources,
    verify_graph_topology,
)
from mkm_long_term_memory_graph_topology_v1 import verify_topology_coverage  # noqa: E402


def _set_json_ptr(obj: dict, ptr: str, value: str) -> None:
    parts = [p for p in ptr.strip("/").split("/") if p]
    cur: dict = obj
    for part in parts[:-1]:
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            nxt = {}
            cur[part] = nxt
        cur = nxt
    if parts:
        cur[parts[-1]] = value


def _ensure_concept_stubs(tmp_path: Path) -> None:
    for spec in CONCEPT_BY_ID.values():
        coord = spec.coordinates[0]
        path = tmp_path / coord.file_path
        missing_tags = list(spec.must_keep_tags)
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            patch = [t for t in missing_tags if t not in text]
            if patch:
                path.write_text(text + "\n" + " ".join(patch), encoding="utf-8")
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        if coord.kind == "json_pointer":
            obj: dict = {}
            filler = " ".join(missing_tags)
            for ptr in coord.json_pointers or ("/value",):
                _set_json_ptr(obj, ptr, filler)
            path.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
        else:
            start = coord.anchor_start or "# stub"
            end_marker = coord.anchor_end or "## end"
            body = " ".join(missing_tags)
            path.write_text(f"{start}\n\n{body}\n\n{end_marker}\n", encoding="utf-8")


def _write_min_ssot(tmp_path: Path) -> None:
    excerpt = tmp_path / "docs/final/artifacts/notebooklm_lens_sasang_rag_excerpt_v1.md"
    excerpt.parent.mkdir(parents=True, exist_ok=True)
    excerpt.write_text(
        "# excerpt\n\n"
        "## Core framing · 태양인 희귀성 (MKM pedagogical SSOT · [HYPO])\n\n"
        "1. **火剋金(화극금):** test\n"
        "2. **金器 containment:** rocket engine [HYPO]\n\n"
        "## Next section\n\n",
        encoding="utf-8",
    )
    bundle = tmp_path / "docs/final/artifacts/sasang_interpretive_insight_bundle_v1_latest.json"
    bundle.write_text(
        json.dumps(
            {
                "synthesis_v1": {
                    "forbidden_synthesis_ko": "금지(B-track) forbidden_synthesis_ko test"
                },
                "human_commander_gate_v1": {"banner_ko": "[HYPO] banner"},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    freeze = tmp_path / "reports/btrack_prophecy_research_freeze_v1_latest.json"
    freeze.parent.mkdir(parents=True, exist_ok=True)
    freeze.write_text(
        json.dumps(
            {
                "research_only": True,
                "production_posture": {"send_gate": "HOLD"},
                "metrics": {
                    "price_hit_rates": {
                        "pooled": {"hit_rate": 0.527778},
                        "kospi": {"hit_rate": 0.572222},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    oper = tmp_path / "reports/btrack_prophecy_score_recommended_eval_chain_v1_latest.json"
    oper.write_text(
        json.dumps({"schema": "btrack_prophecy_score_v1", "generated_at_utc": "2026-06-12T13:13:33Z"}),
        encoding="utf-8",
    )
    closure = tmp_path / "reports/btrack_envelope_benchmark_closure_v1_latest.json"
    closure.write_text(
        json.dumps(
            {
                "research_only": True,
                "decision_tree_outcome": {"branch_id": "similar_or_incomparable_within_ci"},
                "hypothesis_outcomes": {"H2_mkm_better_governance": "affirmed_primary_posture"},
                "oper_score_ssot_read_only": {"kospi_directional_hit_rate_raw": 0.572222},
                "verdict_ko": "research_only CLOSED — SEND HOLD",
            }
        ),
        encoding="utf-8",
    )
    gates = tmp_path / "docs/final/artifacts/prophecy_promotion_gates_v1_latest.json"
    gates.write_text(
        json.dumps(
            {
                "outcome_class": "reject",
                "combined_all_passed": False,
                "gate_taxonomy": {"research_only": True},
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "docs/NotebookLM_sources_manifest.md"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        "| **사상 Sasang (B)** | `LENS_SASANG` | excerpt | `[HYPO]` LENS_SASANG pack |\n"
        "| **명리 Myeongni (B)** | `LENS_MYEONGNI` | excerpt | `[HYPO]` LENS_MYEONGNI pack |\n"
        "| **성경 Logos (B, NON_GATING)** | `LENS_LOGOS` | x | NON_GATING |\n"
        "| **Track C / 사업** | `TRACKC_BIZ` | x | y |\n\n"
        "### MCP `notebooklm-mcp` 인증\n\n"
        "get_health authenticated setup_auth re_auth\n\n"
        "#### 노트북당 소스 한도\n\n",
        encoding="utf-8",
    )
    central_dir = tmp_path / "docs/final"
    (central_dir / "CENTRAL_AGENT_MEMORY_V1.md").write_text(
        "<!-- ATHENA_CHECKPOINT_V1_START -->\n"
        "- CENTRAL checkpoint test\n"
        "<!-- ATHENA_CHECKPOINT_V1_END -->\n\n"
        "| 레짐 주·보 | **1차** `regime_map` 실물 **주** · 2차 성경 **보** — 2차는 **실전 트리거 금지**. |\n"
        "| Multi-Lens | 격벽 |\n",
        encoding="utf-8",
    )
    constitution = central_dir / "CONSTITUTION_INFERENCE_IMPLEMENTATION_FACTS.md"
    constitution.write_text(
        "## 1. 검증 범위\n\nCONSTITUTION pytest exit code SSOT.\n\n"
        "## 2. Dual-regime\n\n"
        "## 28) 실행 거버넌스 (Athena Run · Execution Clearance Certificate)\n\n"
        "ECC DENIED execution_clearance_certificate_v1 integrated_governance_v1\n\n"
        "**명시적 한계(우회):** bypass note\n\n"
        "| 트레이딩 단일 판정 파일 | `build_trading_go_nogo_status_v1.py` trading_go_no_go_latest.json |\n"
        "| Fact-Safe 리스크 주기 갱신 | Run-FactSafeRiskProfileSyncChain sync_fact_safe_risk_profile risk_profile_fact_safe |\n"
        "| 환경 스냅샷 | ops snapshot |\n"
        "| 트레이딩 Human-in-the-Loop | trading_human_execution_approval validate_trading_human_execution_approval_v1 |\n"
        "| 에이전트 레인 분리 | AGENTS.md |\n\n",
        encoding="utf-8",
    )
    local_vps = central_dir / "LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md"
    local_vps.write_text(
        "## 표준 결론 (이 문서가 단일 SSOT)\n\n"
        "코드/전략 동기화 · 실전 주문 ON 별도 승인 · SSOT\n\n"
        "## 역할 표\n\n"
        "| local | vps |\n\n"
        "## 24h 보수 운영 하드라인 (Fact-Lock v1)\n\n"
        "pm2 show exec cwd start_live_trading\n\n"
        "## VPS 배치 (권장): 모노레포 클론 하나\n\n"
        "start_live_trading.py pm2 show\n\n"
        "## VPS에 SSH로 들어갔을 때 (순서 고정)\n\n",
        encoding="utf-8",
    )
    start_live = tmp_path / "projects/bitcoin-trading/start_live_trading.py"
    start_live.parent.mkdir(parents=True, exist_ok=True)
    start_live.write_text(
        '"""\nPM2 / VPS 진입점 start_live_trading pm2 show exec cwd\n"""\n\ndef main():\n    pass\n',
        encoding="utf-8",
    )
    build_go = tmp_path / "scripts/build_trading_go_nogo_status_v1.py"
    build_go.parent.mkdir(parents=True, exist_ok=True)
    build_go.write_text(
        '"""Build single-file trading GO/NO_GO readiness status.\n\n'
        "trading_go_no_go build_trading_go_nogo_status_v1\n"
        'DEFAULT_OUT = "docs/final/artifacts/trading_go_no_go_latest.json"\n',
        encoding="utf-8",
    )
    validate_approval = tmp_path / "scripts/validate_trading_human_execution_approval_v1.py"
    validate_approval.write_text(
        '"""Validate trading_human_execution_approval_v1 JSON.\n\n'
        "Exit codes:\n  0 OK\n",
        encoding="utf-8",
    )
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "## Git · 원격 (한 줄)\n\n"
        "- push-internal.ps1 · 1작업=1브랜치=1PR\n"
        "- Push-GitHub-Explicit.ps1 -Acknowledge 예외만.\n\n"
        "## User Rules\n\n",
        encoding="utf-8",
    )
    worldview = central_dir / "MKM_WORLDVIEW_AND_PHILOSOPHY_CONSTITUTION_V1.md"
    worldview.write_text(
        "### 1.2 시스템 매핑 (3+1 · 렌즈)\n\nworldview body\n\n"
        "## 2. 만물·생장\n\n",
        encoding="utf-8",
    )
    mission = tmp_path / "MISSION_LOG.md"
    mission.write_text(
        "## 🚀 전술 작전 보드\n\nSEND_GATE: HOLD · Track A·실매매 금지\n\n"
        "**다음 1타 (레인 · 새 채팅):**\n\n"
        "| 레인 | 다음 1타 |\n|------|----------|\n"
        "| **MS** | HOLD · 47.5% · apply_forbidden · 금지 |\n"
        "| **압축·Moat (GitHub)** | Moat · SEND_GATE: HOLD · 커뮤니티 PR |\n"
        "| **Track C·GTM·Magic Orb** | 패시브 |\n"
        "| **명리·Interpret [HYPO]** | Pack0B · SEND_GATE: HOLD |\n"
        "| **Design/Showroom** | hub smoke · jemaai |\n"
        "| **환자·최소영 (Track B)** | 종료 |\n\n"
        "### 📦 핸드오프\n\n",
        encoding="utf-8",
    )
    prism = central_dir / "MKM12_PRISM_INDEX_REGISTRY_V1.json"
    prism.write_text(
        json.dumps(
            {
                "schema": "mkm12_prism_index_registry_v1",
                "description": "Grand Indexing 2.0 logical path registry",
                "entries": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    agents = tmp_path / "AGENTS.md"
    agents.write_text(
        "# AGENTS stub\n\n"
        "## Fact-Lock · 격벽 (한 화면)\n\n"
        "렌즈: `사상` / `명리` / `성경(Logos)` — Final Action = 1차 `regime_map` + 운영 게이트.\n"
        "MKM = **4AI core + Absolute Balance Coordinator Mode** (제5 AI/체질 아님).\n\n"
        "## 재개 · 종료\n\n"
        "build_mkm_chat_resume_pack_v1 lane resume\n\n"
        "## Git · 원격 (한 줄)\n\n"
        "push-internal 1작업=1브랜치=1PR Push-GitHub-Explicit.ps1 Acknowledge\n\n"
        "## User Rules\n\n",
        encoding="utf-8",
    )
    _ensure_concept_stubs(tmp_path)


def test_score_concept_taeyang_query() -> None:
    spec = CONCEPT_BY_ID["sasang_taeyang_containment"]
    concept = {
        "essence": spec.essence,
        "label_ko": spec.label_ko,
        "query_aliases": list(spec.query_aliases),
        "field_tags": list(spec.field_tags),
    }
    assert score_concept_query(concept, "왜 태양인이 희귀하지 火剋金") >= 3


def test_build_graph_document_minimal(tmp_path: Path) -> None:
    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    assert doc["schema"] == "mkm_long_term_memory_graph_v1"
    assert doc["concept_count"] == len(CONCEPT_BY_ID)
    assert "sasang_taeyang_containment" in doc["concepts"]
    errors = verify_graph_sources(tmp_path, doc)
    assert errors == []


def test_route_concepts_includes_related(tmp_path: Path) -> None:
    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    routed = route_concepts_by_query(doc, "태양인 火剋金 containment")
    ids = [cid for cid, _ in routed]
    assert "sasang_taeyang_containment" in ids
    assert "sasang_forbidden_synthesis" in ids or "lens_sasang_notebooklm_pack" in ids


def test_route_ms_compression_lane(tmp_path: Path) -> None:
    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    routed = route_concepts_by_query(doc, "MS 압축 47.5 jaccard track a")
    ids = [cid for cid, _ in routed]
    assert "compression_track_a_active_kpi" in ids or "ms_lane_submission_hold" in ids
    assert resolve_lane_from_graph(doc, "MS compression 47.5") == "ms"


def test_topology_covers_all_concepts() -> None:
    errors = verify_topology_coverage(list(CONCEPT_BY_ID.keys()))
    assert errors == []


def test_build_graph_topology_contract(tmp_path: Path) -> None:
    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    assert verify_graph_topology(doc) == []
    for concept in doc["concepts"].values():
        topo = concept.get("topology") or {}
        assert topo.get("software_layer")
        assert topo.get("blast_radius")


def test_route_meta_twelve_ai(tmp_path: Path) -> None:
    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    routed = route_concepts_by_query(doc, "12ai router librarian sentinel routing")
    ids = [cid for cid, _ in routed]
    assert "twelve_ai_routing_contract" in ids


def test_route_infra_scheduler(tmp_path: Path) -> None:
    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    routed = route_concepts_by_query(doc, "solo scheduler parallel passive infra")
    ids = [cid for cid, _ in routed]
    assert "infra_solo_scheduler_stack" in ids or "infra_parallel_passive_loop" in ids
    assert resolve_lane_from_graph(doc, "infra scheduler solo") == "infra"


def test_route_trading_live_guard(tmp_path: Path) -> None:
    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    routed = route_concepts_by_query(doc, "trading go nogo human approval pm2 vps live")
    ids = [cid for cid, _ in routed]
    assert any(
        cid in ids
        for cid in (
            "trading_go_nogo_status_ssot",
            "trading_human_execution_approval_gate",
            "vps_pm2_live_entry_boundary",
        )
    )
    assert resolve_lane_from_graph(doc, "vps pm2 live trading gate") == "infra"


def test_route_a2a_ltm_bridge(tmp_path: Path) -> None:
    _write_min_ssot(tmp_path)
    doc = build_graph_document(tmp_path)
    routed = route_concepts_by_query(doc, "a2a ltm wire encoding smoke track wall forbidden")
    ids = [cid for cid, _ in routed]
    assert "a2a_ltm_track_wall" in ids or "inter_agent_encoding_smoke_chain" in ids
    assert resolve_lane_from_graph(doc, "a2a inter agent encoding") == "infra"
