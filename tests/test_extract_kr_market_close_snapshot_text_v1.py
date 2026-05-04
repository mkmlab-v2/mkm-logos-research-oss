from __future__ import annotations

import subprocess
import sys
from pathlib import Path


_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "extract_kr_market_close_snapshot_text_v1.py"
_RAW = _ROOT / "tests" / "fixtures" / "kr_market_close_snapshot_raw_20260504.html"


def test_extract_close_snapshot_text_from_raw_html(tmp_path: Path) -> None:
    out_text = tmp_path / "snapshot.txt"
    out_json = tmp_path / "snapshot_meta.json"
    cmd = [
        sys.executable,
        str(_SCRIPT),
        "--input",
        str(_RAW),
        "--out-text",
        str(out_text),
        "--out-json",
        str(out_json),
    ]
    proc = subprocess.run(cmd, cwd=str(_ROOT), capture_output=True, text=True, check=False)
    assert proc.returncode == 0, proc.stderr + proc.stdout
    txt = out_text.read_text(encoding="utf-8")
    assert "외국인 +29,308 억원" in txt
    assert "기관 +20,098 억원" in txt
    assert "상승종목수 392" in txt
    assert "하락종목수 476" in txt
    assert "전선 +17.03%" in txt

