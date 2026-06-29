from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]


def test_sasang_role_router_unit() -> None:
    sys.path.insert(0, str(_ROOT))
    from scripts.btrack_sasang_role_router_v1 import (
        classify_lexicon_entry,
        handoff_allowed,
        role_hint_from_4d,
        validate_ops_handoff_chain,
    )

    ent = {
        "atom_id": "greek::και",
        "lang": "greek",
        "normalized_form": "και",
        "occurrences": 19602,
        "lexicon_match_method": "strongs_norm",
        "morphhb_disambiguation": None,
        "morphhb_chosen": None,
    }
    role = classify_lexicon_entry(ent, high_occ_threshold=5000)
    assert role.sasang_role == "taeyang"
    assert handoff_allowed("taeyang", "soyang")
    assert not handoff_allowed("soeumin", "taeyang")
    bad = validate_ops_handoff_chain(["soeumin", "taeyang"])
    assert bad["ok"] is False
    hint = role_hint_from_4d({"S": 0.1, "L": 0.9, "K": 0.2, "M": 0.3})
    assert hint == "soyang"


def test_lexicon_shadow_builder() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/build_btrack_sasang_lexicon_shadow_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (_ROOT / "reports/btrack_sasang_lexicon_shadow_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc.get("codebook_unmodified") is True
    assert doc.get("track_a_bridge") is False
    assert int(doc.get("codebook_entry_count") or 0) >= 1000
    assert len([k for k, v in (doc.get("role_counts") or {}).items() if int(v or 0) > 0]) >= 4


def test_auto_continue_full() -> None:
    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_btrack_sasang_41k_auto_continue_v1.py"), "--skip-logos-pack"],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    doc = json.loads(
        (_ROOT / "reports/btrack_sasang_41k_auto_continue_v1_latest.json").read_text(encoding="utf-8")
    )
    assert doc.get("ok") is True
    assert doc.get("psi_bridge_ok") is True
    bridge = json.loads(
        (_ROOT / "reports/btrack_sasang_psi_role_bridge_v1_latest.json").read_text(encoding="utf-8")
    )
    assert bridge.get("bridge_ok") is True
    assert len(bridge.get("bridged_nodes") or []) >= 4

    cp = subprocess.run(
        [sys.executable, str(_ROOT / "scripts/run_btrack_sasang_41k_hd_chain_v1.py")],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    chain = json.loads(
        (_ROOT / "reports/btrack_sasang_41k_hd_chain_v1_latest.json").read_text(encoding="utf-8")
    )
    assert chain.get("ok") is True
    assert chain.get("completion_pass") is True
    assert float(chain.get("completion_score") or 0) >= 90.0
    board = _ROOT / "reports/btrack_sasang_41k_operator_board_v1_latest.md"
    assert board.is_file()
    assert "codebook 본체 비변경" in board.read_text(encoding="utf-8")
