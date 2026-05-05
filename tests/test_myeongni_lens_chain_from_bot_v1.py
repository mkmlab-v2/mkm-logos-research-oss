# @MKM12-METADATA
# Type: Logic
# Purpose: 봇→융합→명리 렌즈 체인 스모크.

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


def test_chain_demo_smoke_writes_lens(tmp_path: Path) -> None:
    chain = _ROOT / "scripts/run_myeongni_lens_chain_from_bot_v1.py"
    bot_out = tmp_path / "bot.json"
    fus_out = tmp_path / "fusion.json"
    lens_out = tmp_path / "lens.json"
    cp = subprocess.run(
        [
            sys.executable,
            str(chain),
            "--demo-smoke",
            "--bot-out",
            str(bot_out),
            "--fusion-out",
            str(fus_out),
            "--lens-out",
            str(lens_out),
            "--compact",
        ],
        cwd=str(_ROOT),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert cp.returncode == 0, cp.stderr + cp.stdout
    lens_doc = json.loads(lens_out.read_text(encoding="utf-8"))
    assert lens_doc.get("schema") == "myeongni_independent_lens_v1"
    assert bot_out.is_file()
    assert fus_out.is_file()
