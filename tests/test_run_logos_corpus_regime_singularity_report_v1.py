from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts/run_logos_corpus_regime_singularity_report_v1.py"
REGIME = ROOT / "data/regimes/regime_map_btc_ext.json"


def test_logos_singularity_wrapper_smoke(tmp_path: Path) -> None:
    if not REGIME.is_file():
        pytest.skip("regime_map_btc_ext.json missing")
    canon = tmp_path / "canon.jsonl"
    rows = [
        {
            "verse_id": "Gen.1.1",
            "text": "ברא אלהים",
            "original_text": "ברא אלהים",
        },
        {
            "verse_id": "Gen.1.2",
            "text": "ותהי הארץ",
            "original_text": "ותהי הארץ",
        },
    ]
    with canon.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    out = tmp_path / "singularity.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(WRAPPER),
            "--canon-jsonl",
            str(canon),
            "--regime-map-json",
            str(REGIME),
            "--top-n",
            "5",
            "--output-json",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "logos_corpus_regime_singularity_report_v1"
    assert doc["df_mission_id"] == "DF-P2-02"
    assert doc["counts"]["rows_scanned"] >= 1
