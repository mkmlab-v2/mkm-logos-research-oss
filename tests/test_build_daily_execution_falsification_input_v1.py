from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def test_build_daily_execution_falsification_input_v1(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    script = repo / "scripts" / "build_daily_execution_falsification_input_v1.py"

    kospi_csv = tmp_path / "kospi_daily_external_yf.csv"
    kospi_csv.write_text(
        "Date,Close\n2026-05-06,2500\n2026-05-07,2520\n",
        encoding="utf-8",
    )
    myeongni = tmp_path / "myeongni.json"
    sasang = tmp_path / "sasang.json"
    logos = tmp_path / "logos.json"
    out = tmp_path / "daily_execution_falsification_input_latest.json"

    _write_json(myeongni, {"scores": {"direction_score": 0.3}})
    _write_json(sasang, {"scores": {"direction_score": -0.2}})
    _write_json(logos, {"scores": {"direction_score": 0.0}})

    subprocess.run(
        [
            sys.executable,
            str(script),
            "--kospi-csv",
            str(kospi_csv),
            "--myeongni-json",
            str(myeongni),
            "--sasang-json",
            str(sasang),
            "--logos-json",
            str(logos),
            "--out",
            str(out),
        ],
        check=True,
        cwd=repo,
    )

    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["schema"] == "daily_execution_falsification_input_v1"
    assert payload["market_snapshot"]["actual_label"] == "UP"
    entries = {x["lens_id"]: x for x in payload["entries"]}
    assert entries["myeongni"]["prediction_label"] == "UP"
    assert entries["sasang"]["prediction_label"] == "DOWN"
    assert entries["logos"]["prediction_label"] == "NEUTRAL"
