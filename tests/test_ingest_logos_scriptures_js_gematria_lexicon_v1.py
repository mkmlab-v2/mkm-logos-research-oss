"""Smoke: scriptures-js gematria lexicon ingest (fixture sample)."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/ingest_logos_scriptures_js_gematria_lexicon_v1.py"


def test_ingest_fixture_sample():
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "gematria_lexicon.jsonl"
        report = Path(tmp) / "report.json"
        proc = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--use-fixture-sample",
                "--out-jsonl",
                str(out),
                "--report",
                str(report),
                "--min-entries",
                "3",
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0, proc.stderr or proc.stdout
        lines = [json.loads(x) for x in out.read_text(encoding="utf-8").splitlines() if x.strip()]
        assert len(lines) >= 3
        assert all(row.get("schema") == "logos_scriptures_js_gematria_lexicon_entry_v1" for row in lines)
        assert all(row.get("source") == "scriptures_js_gematria" for row in lines)
        assert all(row.get("lookup_only") is True for row in lines)
        assert all(row.get("prophecy_claims") is False for row in lines)
        assert all(row.get("kernel_recipe_id") == "gematria_bridge_v1" for row in lines)
        assert all(set((row.get("vector_4d") or {}).keys()) == {"S", "L", "K", "M"} for row in lines)
        logos = next(r for r in lines if r.get("strongs") == "G3056")
        assert logos["gematria"]["isopsephy_standard"] == 373
        doc = json.loads(report.read_text(encoding="utf-8"))
        assert doc["schema"] == "logos_scriptures_js_gematria_ingest_v1"
        assert doc["send_gate"] == "HOLD"


def test_license_gate_requires_ack():
    proc = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--scriptures-js-dir",
            str(ROOT / "storage/external_kg/scriptures_js_v1"),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert proc.returncode != 0
    assert "ack-license" in (proc.stderr or proc.stdout).lower()


def test_hebrew_bereshit_gematria_fixture():
    from scripts.logos_scriptures_js_gematria_lib_v1 import compute_gematria_for_lemma

    prepared, gem = compute_gematria_for_lemma("רֵאשִׁית", "hebrew")
    assert prepared == "ראשית"
    assert gem["mispar_hechrachi"] == 911
