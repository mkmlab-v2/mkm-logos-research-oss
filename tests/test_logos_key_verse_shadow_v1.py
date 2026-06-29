# @MKM12-METADATA
# Type: Logic
# Purpose: Smoke test key-verse shadow post-it pipeline.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_BUILD = _ROOT / "scripts/build_logos_key_verses_shadow_v1.py"
_ENRICH = _ROOT / "scripts/enrich_logos_path_gate_shadow_persona_v1.py"


def _write_jsonl(path: Path) -> None:
    rows = [
        {
            "schema": "logos_verse_4d_v1",
            "verse_id": "Jhn.1.1",
            "vector_4d": {"S": 0.42, "L": 0.21, "K": 0.2, "M": 0.17},
        },
        {
            "schema": "logos_verse_4d_v1",
            "verse_id": "Dan.2.21",
            "vector_4d": {"S": 0.18, "L": 0.27, "K": 0.33, "M": 0.22},
        },
    ]
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def test_build_and_enrich_shadow(tmp_path: Path) -> None:
    verse_jsonl = tmp_path / "verse.jsonl"
    _write_jsonl(verse_jsonl)

    gate = tmp_path / "gate.json"
    gate.write_text(
        json.dumps(
            {
                "schema": "logos_path_verification_gate_v1",
                "summary": {"gate_pass": True, "pass_rate": 1.0},
                "checks": [
                    {
                        "unit_id": "u1",
                        "v_score": 1,
                        "citations": ["Jhn.1.1", "Dan.2.21"],
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    shadow = tmp_path / "shadow.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(_BUILD),
            "--verse-jsonl",
            str(verse_jsonl),
            "--path-gate",
            str(gate),
            "--out",
            str(shadow),
            "--top-n",
            "16",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr
    doc = json.loads(shadow.read_text(encoding="utf-8"))
    assert doc["schema"] == "verse_metadata_shadow_v1"
    assert doc["summary"]["shadow_rows"] >= 1

    cp2 = subprocess.run(
        [
            sys.executable,
            str(_ENRICH),
            "--gate",
            str(gate),
            "--shadow",
            str(shadow),
            "--out",
            str(gate),
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp2.returncode == 0, cp2.stderr
    gdoc = json.loads(gate.read_text(encoding="utf-8"))
    check = gdoc["checks"][0]
    assert check["shadow_persona_hint"]
    assert gdoc["summary"]["gate_pass"] is True
