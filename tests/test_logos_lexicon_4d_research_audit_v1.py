# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test logos 41k 4D reclassification audit + orchestrator (Track B).
# Keywords: logos, lexicon_4d, gematria, path_shadow

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_BUILD = _ROOT / "scripts/build_logos_41k_4d_reclassification_audit_v1.py"
_ENRICH = _ROOT / "scripts/enrich_logos_path_gate_4d_shadow_v1.py"
_ORCH = _ROOT / "scripts/run_logos_lexicon_4d_research_audit_v1.py"


def _minimal_verse(verse_id: str, text: str, vec: dict[str, float]) -> dict:
    return {
        "schema": "logos_verse_4d_v1",
        "version": "1.0.0",
        "verse_id": verse_id,
        "text_span": {"original_script_text": text},
        "vector_4d": vec,
    }


def _tiny_codebook(tmp_path: Path) -> Path:
    p = tmp_path / "master_codebook_lexicon_v1_3_rows_latest.json"
    p.write_text(
        json.dumps(
            {
                "schema": "master_codebook_lexicon_v1",
                "row_count": 3,
                "entries": [
                    {"atom_id": "hebrew::ברא", "lang": "hebrew", "normalized_form": "ברא", "occurrences": 10},
                    {"atom_id": "hebrew::אלהים", "lang": "hebrew", "normalized_form": "אלהים", "occurrences": 8},
                    {"atom_id": "greek::θεός", "lang": "greek", "normalized_form": "θεός", "occurrences": 5},
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return p


def test_build_41k_4d_audit_and_shadow_enrich(tmp_path: Path) -> None:
    verse_jsonl = tmp_path / "verses.jsonl"
    v1 = _minimal_verse("Jhn.1.1", "בְּרֵאשִׁית ברא אלהים", {"S": 0.3, "L": 0.25, "K": 0.25, "M": 0.2})
    v2 = _minimal_verse("Jhn.1.2", "ברא אלהים", {"S": 0.31, "L": 0.24, "K": 0.26, "M": 0.19})
    with verse_jsonl.open("w", encoding="utf-8") as f:
        f.write(json.dumps(v1, ensure_ascii=False) + "\n")
        f.write(json.dumps(v2, ensure_ascii=False) + "\n")

    codebook = _tiny_codebook(tmp_path)
    lexicon_out = tmp_path / "lexicon_4d.json"
    proj = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts/project_logos_verse_4d_to_lexicon_v1.py"),
            "--verse-jsonl",
            str(verse_jsonl),
            "--codebook-json",
            str(codebook),
            "--min-verse-count-for-lexicon",
            "1",
            "--out-lexicon-4d-json",
            str(lexicon_out),
            "--out-jsonl",
            str(tmp_path / "overlay.jsonl"),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proj.returncode == 0, proj.stderr

    gate_path = tmp_path / "gate.json"
    gate_path.write_text(
        json.dumps(
            {
                "schema": "logos_path_verification_gate_v1",
                "summary": {"gate_pass": True, "pass_rate": 1.0},
                "checks": [
                    {
                        "unit_id": "u1",
                        "v_score": 1,
                        "citations": ["Jhn.1.1", "Jhn.1.2"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    audit_out = tmp_path / "audit.json"
    build = subprocess.run(
        [
            sys.executable,
            str(_BUILD),
            "--lexicon-4d",
            str(lexicon_out),
            "--codebook-json",
            str(codebook),
            "--verse-jsonl",
            str(verse_jsonl),
            "--path-gate",
            str(gate_path),
            "--residual",
            str(tmp_path / "missing_residual.json"),
            "--out",
            str(audit_out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert build.returncode == 0, build.stderr
    audit = json.loads(audit_out.read_text(encoding="utf-8"))
    assert audit["schema"] == "logos_41k_4d_reclassification_audit_v1"
    assert audit["ok"] is True
    assert audit["phase_pb_lexicon_coverage"]["lexicon_4d_row_count"] >= 1
    shadow = audit["phase_pc_path_four_d_shadow"]
    assert shadow["does_not_affect_gate_pass"] is True
    assert shadow["mean_four_d_coherence"] is not None

    enrich = subprocess.run(
        [
            sys.executable,
            str(_ENRICH),
            "--gate",
            str(gate_path),
            "--audit",
            str(audit_out),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert enrich.returncode == 0, enrich.stderr
    enriched = json.loads(gate_path.read_text(encoding="utf-8"))
    assert enriched["summary"]["gate_pass"] is True
    assert "four_d_shadow" in enriched


@pytest.mark.slow
def test_orchestrator_skip_pa_smoke() -> None:
    proc = subprocess.run(
        [
            sys.executable,
            str(_ORCH),
            "--skip-phase-pa",
            "--max-verse-rows",
            "200",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=3600,
    )
    assert proc.returncode == 0, proc.stderr[-800:]
    out = _ROOT / "reports/logos_lexicon_4d_research_audit_v1_latest.json"
    doc = json.loads(out.read_text(encoding="utf-8-sig"))
    assert doc.get("ok") is True
