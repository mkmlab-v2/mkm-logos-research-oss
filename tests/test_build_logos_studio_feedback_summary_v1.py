from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_build_logos_studio_feedback_summary_smoke(tmp_path: Path) -> None:
    src = tmp_path / "feedback.jsonl"
    out = tmp_path / "feedback_summary.json"
    src.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "ts_utc": "2026-06-25T08:00:00Z",
                        "verdict": "up",
                        "issue_type": "context",
                        "evidence_anchor": "Gen 6:4",
                    }
                ),
                json.dumps(
                    {
                        "ts_utc": "2026-06-25T09:00:00Z",
                        "verdict": "down",
                        "issue_type": "translation",
                        "evidence_anchor": "Gen 6:4",
                    }
                ),
                json.dumps(
                    {
                        "ts_utc": "2026-06-25T10:00:00Z",
                        "verdict": "up",
                        "issue_type": "source",
                        "evidence_anchor": "Enoch 7:2",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/build_logos_studio_feedback_summary_v1.py"),
            "--feedback-jsonl",
            str(src),
            "--out-json",
            str(out),
            "--window-days",
            "3650",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stdout + proc.stderr
    doc = json.loads(out.read_text(encoding="utf-8"))
    assert doc.get("schema") == "logos_studio_feedback_summary_v1"
    assert ((doc.get("counts") or {}).get("total")) == 3
    assert ((doc.get("counts") or {}).get("up")) == 2
    assert ((doc.get("counts") or {}).get("down")) == 1
    assert ((doc.get("top_issue_types") or {}).get("translation")) == 1
    assert (((doc.get("windows") or {}).get("w7") or {}).get("counts") or {}).get("total") == 3

