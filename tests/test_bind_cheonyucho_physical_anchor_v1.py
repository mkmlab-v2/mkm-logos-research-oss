"""Tests for bind_cheonyucho_physical_anchor paste validation and ingest."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BIND = ROOT / "scripts" / "bind_cheonyucho_physical_anchor_v1.py"


def test_validate_transcript_warns_low_hanja() -> None:
    sys.path.insert(0, str(ROOT / "scripts"))
    from bind_cheonyucho_physical_anchor_v1 import validate_transcript

    v = validate_transcript("목차만 있고 한글 위주입니다. 천유초 편.")
    assert v["accept_paste"] is True
    assert v["warnings"]


def test_bind_paste_writes_proxy_and_anchor(tmp_path: Path) -> None:
    paste = tmp_path / "sample.txt"
    paste.write_text(
        "闡幽抄曰 太陰人病證 呼散不足 吸聚有餘 此段為測試貼上용 paste gate sample.\n",
        encoding="utf-8",
    )
    probe = tmp_path / "probe.json"
    probe.write_text(
        json.dumps(
            {
                "schema": "cheonyucho_acquisition_probe_v1",
                "track": "B",
                "send_gate": "HOLD",
                "hanja_canon_status": "not_acquired",
                "checklist": [{"id": "P1-01", "status": "pending_physical_book"}],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    anchor_out = tmp_path / "anchor.json"
    slug = "pytest_paste"

    cp = subprocess.run(
        [
            sys.executable,
            str(BIND),
            "--paste-file",
            str(paste),
            "--slug",
            slug,
            "--call-no",
            "199.1-이617ㄱ",
            "--page",
            "index-smoke",
            "--probe",
            str(probe),
            "--anchor-out",
            str(anchor_out),
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    assert cp.returncode == 0, cp.stderr or cp.stdout
    line = [ln for ln in cp.stdout.splitlines() if ln.strip().startswith("{")][-1]
    out = json.loads(line)
    assert out["ok"] is True
    assert out["transcript_sha256"]
    assert out["hanja_canon_status"] == "not_acquired"

    anchor = json.loads(anchor_out.read_text(encoding="utf-8"))
    assert anchor["hanja_canon_status"] == "not_acquired"
    assert anchor["transcript_sha256"] == out["transcript_sha256"]

    proxy = ROOT / "docs/research/raw" / f"CHEONYUCHO_PHYSICAL_{slug}_nl_proxy.md"
    assert proxy.is_file()
    proxy.unlink(missing_ok=True)
