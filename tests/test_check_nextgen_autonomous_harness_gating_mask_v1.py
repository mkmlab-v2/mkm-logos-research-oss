from __future__ import annotations

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASK_STUB = (
    ROOT
    / "experiments/nextgen_clean_slate_cpu_v1/AUTONOMOUS_HARNESS_GATING_MASK_STUB_V1.json"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "check_nextgen_autonomous_harness_gating_mask_v1",
        ROOT / "scripts/check_nextgen_autonomous_harness_gating_mask_v1.py",
    )
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(mod)
    return mod


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def test_mask_stub_schema_fields() -> None:
    mask = _read(MASK_STUB)
    assert mask["schema"] == "autonomous_harness_gating_mask_stub_v1"
    assert mask["research_only"] is True
    assert mask["track_a_active_write"] is False
    assert len(mask["reference_briefings"]) >= 2
    assert all(b["promotion_weight"] == 0 for b in mask["reference_briefings"])


def test_evaluate_passes_with_repo_fixtures() -> None:
    mod = _load()
    mask = _read(MASK_STUB)
    symbolic_path = (
        ROOT
        / "experiments/nextgen_clean_slate_cpu_v1/SYMBOLIC_ARCHETYPE_PREDICTIVE_INDEX_STUB_V1.json"
    )
    topology_path = ROOT / "experiments/nextgen_clean_slate_cpu_v1/topology_spec_v1_latest.json"
    charter_path = ROOT / "reports/btrack_nextgen_indexer_charter_v1_latest.json"

    doc = mod.evaluate(
        mask=mask,
        symbolic=_read(symbolic_path) if symbolic_path.is_file() else None,
        topology=_read(topology_path) if topology_path.is_file() else None,
        charter=_read(charter_path) if charter_path.is_file() else None,
    )
    assert doc["combined_all_passed"] is True
    assert doc["human_signoff_required_for_promotion"] is True
    assert doc["track_a_active_write"] is False


def test_sandbox_chain_includes_g0_harness_gating_on_dry_run() -> None:
    import scripts.run_nextgen_clean_slate_cpu_sandbox_chain_v1 as chain_mod

    doc = chain_mod.build_plan(
        execute=False,
        aux_host=None,
        aux_ip=None,
        main_only=True,
    )
    g0 = [s for s in doc["steps"] if s.get("step_id") == "G0_harness_gating_mask"]
    assert len(g0) == 1
    assert g0[0]["status"] == "ok"
    assert g0[0]["exit_code"] == 0


def test_evaluate_rejects_bad_briefing_weight() -> None:
    mod = _load()
    mask = _read(MASK_STUB)
    mask = dict(mask)
    mask["reference_briefings"] = [
        {
            "source_id": "bad",
            "role": "manual_reference_only",
            "promotion_weight": 1,
        }
    ]
    doc = mod.evaluate(mask=mask, symbolic=None, topology=None, charter=None)
    assert doc["combined_all_passed"] is False
    assert doc["outcome_class"] == "reject"
