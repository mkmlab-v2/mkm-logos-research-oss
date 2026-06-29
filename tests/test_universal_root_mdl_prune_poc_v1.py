"""MDL prune PoC smoke tests (CPU, small sweep)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POC = ROOT / "scripts/run_universal_root_mdl_prune_poc_v1.py"


def test_mdl_prune_lib_must_keep() -> None:
    sys.path.insert(0, str(ROOT))
    from scripts.universal_root_mdl_prune_lib_v1 import must_keep_reason, prune_lexicon_entries

    golden = frozenset({"bible", "covenant"})
    entries = [
        {"atom_id": "x1", "normalized_form": "bible", "occurrences": 1},
        {"atom_id": "x2", "normalized_form": "zzzz", "occurrences": 0},
        {"atom_id": "H1234", "normalized_form": "alpha", "occurrences": 0, "lexicon_strongs_candidates": ["H1234"]},
    ]
    kept, meta = prune_lexicon_entries(entries, target_reduction_pct=50.0, golden_tokens=golden)
    assert len(kept) >= 2
    assert meta["must_keep_count"] >= 2
    assert must_keep_reason(entries[0], golden) == "golden40_surface_hit"


def test_mdl_prune_poc_single_sweep(tmp_path: Path) -> None:
    scratch = tmp_path / "scratch"
    out = tmp_path / "poc.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(POC),
            "--scratch-dir",
            str(scratch),
            "--out",
            str(out),
            "--sweep-pcts",
            "5",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr or proc.stdout
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc["schema"] == "universal_root_mdl_prune_poc_v1"
    assert doc["send_gate"] == "HOLD"
    assert len(doc.get("sweep_rows") or []) == 1
    assert doc.get("baseline_jaccard") is not None
