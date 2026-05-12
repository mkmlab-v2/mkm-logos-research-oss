from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_lens_music_hormone_trend_watch(tmp_path):
    hist = tmp_path / "hist.jsonl"
    rows = [
        {"ts_utc": "2026-05-10T10:00:00Z", "hormone_state": "HIGH_STRESS", "stress_index_0_1": 0.81},
        {"ts_utc": "2026-05-10T10:10:00Z", "hormone_state": "HIGH_STRESS", "stress_index_0_1": 0.79},
        {"ts_utc": "2026-05-10T10:20:00Z", "hormone_state": "HIGH_STRESS", "stress_index_0_1": 0.77},
        {"ts_utc": "2026-05-11T11:00:00Z", "hormone_state": "STABLE", "stress_index_0_1": 0.32},
    ]
    hist.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8")

    out = tmp_path / "trend.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_hormone_trend_v1.py"),
            "--history-log-jsonl",
            str(hist),
            "--high-stress-rate-watch-threshold",
            "0.25",
            "--high-stress-consecutive-watch-threshold",
            "3",
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["schema"] == "lens_music_hormone_trend_v1"
    assert doc["rows_scanned"] == 4
    assert doc["high_stress_count"] == 3
    assert doc["max_consecutive_high_stress"] == 3
    assert doc["state"] == "WATCH"


def test_build_lens_music_hormone_trend_nodata_sets_operator_hint(tmp_path):
    hist = tmp_path / "hist.jsonl"
    hist.write_text('{"ts_utc": "2026-05-10T10:00:00Z", "note": "no hormone_state"}\n', encoding="utf-8")
    out = tmp_path / "trend.json"
    r = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_lens_music_hormone_trend_v1.py"),
            "--history-log-jsonl",
            str(hist),
            "--out",
            str(out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    assert r.returncode == 0, r.stdout + r.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc["state"] == "NODATA"
    assert doc["rows_scanned"] == 0
    assert "operator_hint" in doc
    assert "build_lens_music_prompt_overlay_v1.py" in doc["operator_hint"]
