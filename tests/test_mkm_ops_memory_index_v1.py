"""Tests for MKM ops memory index builder and must_keep gate ([HYPO])."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
    LANE_OPS_PACKS,
    apply_repair_v2_noise_guard,
    build_index_document,
    extract_anchor_block,
    missing_must_keep_tags,
    nodes_for_resume,
    truncate_anchor_slice,
    verify_index_sources,
)


def test_extract_anchor_block_by_markers() -> None:
    lines = [
        "# title\n",
        "## 🚀 전술 작전 보드\n",
        "line-a\n",
        "### 📦 핸드오ff\n",
        "skip-me\n",
    ]
    block, (start, end) = extract_anchor_block(
        lines,
        anchor_start="## 🚀 전술 작전 보드",
        anchor_end="### 📦 핸드오ff",
    )
    assert "line-a" in block
    assert "skip-me" not in block
    assert start == 2
    assert end == 3


def test_must_keep_gate_detects_missing_tag() -> None:
    missing = missing_must_keep_tags("hello world", ["hello", "FORBIDDEN_TAG"])
    assert missing == ["FORBIDDEN_TAG"]


def test_build_index_document_with_fixtures(tmp_path: Path) -> None:
    mission = tmp_path / "MISSION_LOG.md"
    mission.write_text(
        "# MISSION_LOG\n\n"
        "**다음 1타 (레인 · 재개용 핀):**\n\n"
        "| **Oracle·Logos** | **금지:** Track A·live · **HOLD** |\n"
        "| **MS·지원사업** | **SEND_GATE: HOLD** · **금지:** grant paste |\n"
        "**Design/Showroom (아카이브·패시브):** **금지:** Track A · **SEND_GATE: HOLD**\n\n"
        "## 🚀 전술 작전 보드\n\n"
        "### 💼 MS\n\n"
        "**금지:** Track A · FAIL-COMP-004\n"
        "SEND_GATE: HOLD\n\n"
        "### 🧭 Cursor IDE\n\n"
        "cursor\n\n"
        "### 🔮 Oracle\n\n"
        "**금지:** Track A · B-track only\n\n"
        "### 🖥️ Infra\n\n"
        "**금지:** Track A · solo stack\n\n"
        "<!-- MISSION_LOG_BOARD_END -->\n",
        encoding="utf-8",
    )
    central_dir = tmp_path / "docs" / "final"
    central_dir.mkdir(parents=True)
    central = central_dir / "CENTRAL_AGENT_MEMORY_V1.md"
    central.write_text(
        "# CENTRAL\n\n"
        "<!-- ATHENA_CHECKPOINT_V1_START -->\n"
        "<!-- CENTRAL checkpoint block -->\n"
        "- MISSION_LOG research_only 금지 weekly\n"
        "<!-- ATHENA_CHECKPOINT_V1_END -->\n",
        encoding="utf-8",
    )

    doc = build_index_document(tmp_path)
    assert doc["research_only"] is True
    assert len(doc["nodes"]) == 7
    errors = verify_index_sources(tmp_path, doc)
    assert errors == []


def test_nodes_for_resume_lane_oracle(tmp_path: Path) -> None:
    mission = tmp_path / "MISSION_LOG.md"
    mission.write_text(
        "# MISSION_LOG\n\n"
        "**다음 1타 (레인 · 재개용 핀):**\n\n"
        "| **Oracle·Logos** | **금지:** Track A · **HOLD** |\n"
        "**Design/Showroom (아카이브·패시브):** **금지:** Track A · **SEND_GATE: HOLD**\n\n"
        "## 🚀 전술 작전 보드\n\n"
        "FAIL-COMP-004 · Track A · SEND_GATE: HOLD\n\n"
        "### 💼 MS\n\n"
        "**MS** row · **금지:** portal · SEND_GATE HOLD\n\n"
        "### 🧭 Cursor IDE\n\n"
        "### 🔮 Oracle\n\n"
        "**금지:** Track A · B-track\n\n"
        "### 🖥️ Infra\n\n"
        "**금지:** Track A · solo\n\n"
        "<!-- MISSION_LOG_BOARD_END -->\n",
        encoding="utf-8",
    )
    central_dir = tmp_path / "docs" / "final"
    central_dir.mkdir(parents=True)
    (central_dir / "CENTRAL_AGENT_MEMORY_V1.md").write_text(
        "<!-- ATHENA_CHECKPOINT_V1_START -->\n"
        "<!-- CENTRAL checkpoint block -->\n"
        "- MISSION_LOG research_only 금지 checkpoint\n"
        "<!-- ATHENA_CHECKPOINT_V1_END -->\n",
        encoding="utf-8",
    )
    doc = build_index_document(tmp_path)
    lane_ids = [nid for nid, _ in nodes_for_resume(doc, lane="ms", root=tmp_path)]
    assert lane_ids[:3] == [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_ms",
    ]
    assert "prism_ops_mission_log_next_one" not in lane_ids
    assert "prism_ops_lane_oracle" not in lane_ids
    assert "prism_ops_lane_infra" not in lane_ids
    assert "prism_ops_lane_design" not in lane_ids

    reports = tmp_path / "reports"
    reports.mkdir(parents=True)
    (reports / "mkmlife_pixel_sprite_urls_gate_v1_latest.json").write_text(
        json.dumps(
            {
                "overall_ok": True,
                "ok_count": 1,
                "fail_count": 0,
                "track_wall": "B-track UI",
                "hypothesis_tag": "[HYPO]",
                "lane": "research_only",
            }
        ),
        encoding="utf-8",
    )
    (reports / "audio_gate_latest.json").write_text(
        json.dumps(
            {
                "decision": "PASS",
                "track": "B",
                "metrics": {"lens_alignment_pass": True},
                "provenance": {"commercial_terms_tag": "apache2_self_host_weights_v1"},
            }
        ),
        encoding="utf-8",
    )
    design_ids = [nid for nid, _ in nodes_for_resume(doc, lane="design", root=tmp_path)]
    assert design_ids == [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_lane_design",
        "prism_ops_pixel_battalion_gate",
        "prism_ops_lens_audio_gate",
    ]

    out = tmp_path / "storage" / "meta" / "index.json"
    out.parent.mkdir(parents=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding="utf-8")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["nodes"]["prism_ops_mission_log_board"]["line_range"][0] == 8


def test_nodes_for_resume_commander_default(tmp_path: Path) -> None:
    mission = tmp_path / "MISSION_LOG.md"
    mission.write_text(
        "# MISSION_LOG\n\n"
        "**다음 1타 (레인 · 재개용 핀):**\n\n"
        "| **Oracle·Logos** | **금지:** Track A · **HOLD** |\n"
        "**Design/Showroom (아카이브·패시브):** **금지:** Track A · **SEND_GATE: HOLD**\n\n"
        "## 🚀 전술 작전 보드\n\n"
        "FAIL-COMP-004 · Track A · SEND_GATE: HOLD\n\n"
        "### 💼 MS\n\n"
        "**MS** · **금지:** portal · SEND_GATE HOLD\n\n"
        "### 🧭 Cursor IDE\n\n"
        "### 🔮 Oracle\n\n"
        "**금지:** Track A · B-track\n\n"
        "### 🖥️ Infra\n\n"
        "**금지:** Track A · solo\n\n"
        "<!-- MISSION_LOG_BOARD_END -->\n",
        encoding="utf-8",
    )
    central_dir = tmp_path / "docs" / "final"
    central_dir.mkdir(parents=True)
    (central_dir / "CENTRAL_AGENT_MEMORY_V1.md").write_text(
        "<!-- ATHENA_CHECKPOINT_V1_START -->\n"
        "<!-- CENTRAL checkpoint block -->\n"
        "- checkpoint line\n"
        "<!-- ATHENA_CHECKPOINT_V1_END -->\n",
        encoding="utf-8",
    )
    doc = build_index_document(tmp_path)
    ids = [nid for nid, _ in nodes_for_resume(doc, commander_default=True)]
    assert ids == [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_mission_log_next_one",
    ]
    # Portfolio pin appears when snapshot exists (commander_default + root).
    snap_dir = tmp_path / "docs" / "final" / "artifacts"
    snap_dir.mkdir(parents=True, exist_ok=True)
    (snap_dir / "mkm_portfolio_status_snapshot_v1_latest.json").write_text(
        json.dumps(
            {
                "commercialization_phases": {
                    "execution_focus_2026_07": (
                        "one_cash_cow_acodeai + one_passion_logos; "
                        "hold mkmlife/personadiary/gyeokmul after phase1 min"
                    ),
                    "phase_1": "a-codeai PoC [done] · logos pilot [done]",
                },
                "market_validation_advisory_2026_07": {
                    "status": "ADVISORY_not_fact_lock",
                    "compression_lane": "wide_market_crowded_evidence_gap",
                    "logos_lane": "narrow_niche_institution_wtp_unproven_pmf",
                    "ssot": "TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md §0.6",
                },
                "doc_pointers": {
                    "portfolio_master_index": "docs/final/MKM_PORTFOLIO_MASTER_INDEX_V1.md",
                    "business_plan_ssot": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    ids_with = [
        nid
        for nid, _ in nodes_for_resume(
            doc, commander_default=True, root=tmp_path
        )
    ]
    assert ids_with == [
        "prism_ops_mission_log_board",
        "prism_ops_central_checkpoint",
        "prism_ops_mission_log_next_one",
        "prism_ops_portfolio_execution_focus",
    ]


def test_gate_fails_when_tag_stripped(tmp_path: Path) -> None:
    mission = tmp_path / "MISSION_LOG.md"
    mission.write_text(
        "**다음 1타 (레인 · 재개용 핀):**\n\n"
        "| lane | next |\n\n"
        "## 🚀 전술 작전 보드\n\n"
        "Track A only — bulk tag removed\n\n"
        "SEND_GATE: HOLD\n\n"
        "<!-- MISSION_LOG_BOARD_END -->\n",
        encoding="utf-8",
    )
    central_dir = tmp_path / "docs" / "final"
    central_dir.mkdir(parents=True)
    (central_dir / "CENTRAL_AGENT_MEMORY_V1.md").write_text(
        "<!-- ATHENA_CHECKPOINT_V1_START -->\n"
        "- MISSION_LOG research_only 금지 checkpoint\n"
        "<!-- ATHENA_CHECKPOINT_V1_END -->\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="must_keep_tags missing"):
        build_index_document(tmp_path)


def test_truncate_anchor_slice_marks_overflow() -> None:
    text = "a" * 200
    preview, truncated = truncate_anchor_slice(text, max_chars=50)
    assert truncated is True
    assert "HYPO slice truncated" in preview
    assert len(preview) <= 50


def test_reapply_persisted_overlays_restores_logos_math_after_base_rebuild() -> None:
    from mkm_ops_memory_index_lib_v1 import (  # noqa: E402
        load_index,
        reapply_persisted_overlays,
    )

    index = load_index(ROOT / "storage/meta/mkm_ops_memory_index_v1.json")
    base_nodes = {
        k: v
        for k, v in (index.get("nodes") or {}).items()
        if not str(k).startswith("prism_ops_logos_")
    }
    stripped = {**index, "nodes": base_nodes, "overlays": [], "index_version": "1.0"}
    restored = reapply_persisted_overlays(ROOT, stripped, ["logos_math_v1"])
    nodes = restored.get("nodes") or {}
    assert "prism_ops_logos_cosmic_anchor_bridge" in nodes
    assert "logos_math_v1" in (restored.get("overlays") or [])
    assert sum(1 for k in nodes if str(k).startswith("prism_ops_logos_")) >= 4


def test_build_index_preserves_logos_overlay_on_disk(tmp_path: Path) -> None:
    """Bare index rebuild must not wipe logos_math_v1 when prior index had it."""
    live_index = ROOT / "storage/meta/mkm_ops_memory_index_v1.json"
    if not live_index.is_file():
        pytest.skip("live ops index missing")

    prior = json.loads(live_index.read_text(encoding="utf-8-sig"))
    if "logos_math_v1" not in (prior.get("overlays") or []):
        pytest.skip("logos_math_v1 overlay not present on disk")

    out = tmp_path / "mkm_ops_memory_index_v1.json"
    out.write_text(json.dumps(prior, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    proc = subprocess.run(
        [
            sys.executable,
            "scripts/build_mkm_ops_memory_index_v1.py",
            "--workspace-root",
            str(ROOT),
            "--out",
            str(out),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    nodes = doc.get("nodes") or {}
    assert "logos_math_v1" in (doc.get("overlays") or [])
    assert "prism_ops_logos_cosmic_anchor_bridge" in nodes


def test_lane_packs_do_not_mix_foreign_lane_nodes() -> None:
    """Each lane inject must not pull another lane's prism_ops_lane_* pin."""
    lane_node = {
        "ms": "prism_ops_lane_ms",
        "oracle": "prism_ops_lane_oracle",
        "infra": "prism_ops_lane_infra",
        "design": "prism_ops_lane_design",
    }
    for lane, pack in LANE_OPS_PACKS.items():
        foreign = {nid for other, nid in lane_node.items() if other != lane}
        assert not (set(pack) & foreign), f"{lane} pack mixes foreign lane nodes"


def test_resume_pack_cli_default_top_n_is_three() -> None:
    src = (ROOT / "scripts" / "build_mkm_chat_resume_pack_v1.py").read_text(encoding="utf-8")
    assert '"--top-n"' in src or "'--top-n'" in src
    assert "default=3" in src


def test_repair_v2_noise_guard_falls_back_to_baseline() -> None:
    query = "prism notebooklm pointer SSOT"
    baseline = "prism_notebooklm_log_metabolism_core_bridge_pointer prism S SSOT"
    bloated = baseline + "\n" + ("noise token " * 120)
    out = apply_repair_v2_noise_guard(query, baseline_text=baseline, repair_text=bloated)
    assert out == baseline


def test_repair_v2_noise_guard_keeps_improving_repair() -> None:
    query = "compression fact-lock scripts"
    baseline = "compression lane"
    improved = baseline + "\nscripts pytest fact-lock evaluate_report"
    out = apply_repair_v2_noise_guard(query, baseline_text=baseline, repair_text=improved)
    assert out == improved


def test_repair_v2_noise_guard_rejects_marginal_bulk_on_drift() -> None:
    query = "prism_btrack_insight_bridge_inventory_latest prism M SSOT"
    baseline = "x" * 252
    marginal = baseline + "\n" + ("registry drift noise " * 80)
    out = apply_repair_v2_noise_guard(
        query,
        baseline_text=baseline,
        repair_text=marginal,
        mutation="stale_sha",
    )
    assert out == baseline
