# Keywords: comparative_theology, imagination_path, fact_lock, shadow_lane_v3, digest, four_slot

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEED_16 = ROOT / "docs/final/artifacts/comparative_theology_seeds/job_1_6_satan_v1.json"
SEED_23 = ROOT / "docs/final/artifacts/comparative_theology_seeds/job_2_3_blameless_permission_v1.json"
PANORAMA = ROOT / "docs/final/artifacts/comparative_theology_panorama_v1_latest.json"
DIGEST = ROOT / "docs/final/artifacts/comparative_theology_panorama_digest_v1_latest.json"
FOUR_SLOT = ROOT / "docs/final/artifacts/logos_four_slot_generation_envelope_v1_latest.json"
V3_SHOWROOM = (
    ROOT / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_research_shadow_lane_v3.json"
)


def test_comparator_cli_exit_0() -> None:
    for anchor in ("Job.1.6", "Job.2.3"):
        r = subprocess.run(
            [sys.executable, str(ROOT / "scripts/run_theological_school_comparator_v1.py"), "--anchor", anchor],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
        )
        assert r.returncode == 0, r.stderr + r.stdout


def test_panorama_fact_lock_isolation() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_comparative_theology_panorama_v1.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    doc = json.loads(PANORAMA.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "comparative_theology_panorama_v1"
    assert doc["fact_lock"]["send_gate"] == "HOLD"
    for lane in doc["school_lanes"]:
        assert lane["utterance_class"] in ("imagination_path", "unknown_gap")
        assert lane["must_not_present_as_fact"] is True
    assert doc["anchor_corpus"]["utterance_class"] == "corpus_bound"


def test_digest_two_anchors() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_comparative_theology_panorama_digest_v1.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    doc = json.loads(DIGEST.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "comparative_theology_panorama_digest_v1"
    assert doc["entry_count"] >= 2
    refs = {e["anchor_ref"] for e in doc["panorama_entries"]}
    assert "Job.1.6" in refs and "Job.2.3" in refs


def test_four_slot_envelope() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_comparative_theology_panorama_digest_v1.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_four_slot_generation_envelope_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(FOUR_SLOT.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "logos_four_slot_generation_envelope_v1"
    assert doc["slots"]["corpus_bound"]["required"] is True
    assert doc["enforcement"]["llm_autofill_for_schools"] is False


def test_v3_bundle_includes_digest_and_four_slot() -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_research_shadow_lane_v2_bundle_v1.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_comparative_theology_panorama_digest_v1.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_logos_four_slot_generation_envelope_v1.py")],
        cwd=str(ROOT),
        check=True,
        capture_output=True,
    )
    r = subprocess.run(
        [sys.executable, str(ROOT / "scripts/build_research_shadow_lane_v3_bundle_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stderr + r.stdout
    doc = json.loads(V3_SHOWROOM.read_text(encoding="utf-8"))
    assert doc["schema_version"] == "research_shadow_lane_v3_bundle_v1"
    digest = doc["layers"]["comparative_theology"]
    assert digest["schema_version"] == "comparative_theology_panorama_digest_v1"
    assert doc["layers"]["four_slot_contract"]["schema_version"] == "logos_four_slot_generation_envelope_v1"
    assert doc["comparative_panorama_summary"]["entry_count"] >= 2


def test_seed_files_present() -> None:
    for path in (SEED_16, SEED_23):
        seed = json.loads(path.read_text(encoding="utf-8"))
        assert seed["schema"] == "comparative_theology_seed_v1"
