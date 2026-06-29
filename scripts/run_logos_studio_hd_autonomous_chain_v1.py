#!/usr/bin/env python3
"""HD autonomous chain: Logos Studio tier-2 embedding + mobile shell + smoke."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable


def _run(label: str, cmd: list[str]) -> int:
    print(f"[hd-logos] {label}")
    proc = subprocess.run(cmd, cwd=ROOT)
    if proc.returncode != 0:
        print(f"[hd-logos] FAIL {label} exit={proc.returncode}", file=sys.stderr)
    return proc.returncode


def main() -> int:
    steps = [
        ("preset_expansion", [PY, "scripts/run_logos_studio_preset_expansion_chain_v1.py", "--skip-build-base"]),
        ("embedding_index", [PY, "scripts/build_logos_studio_semantic_router_embedding_index_v1.py"]),
        ("mobile_shell", [PY, "scripts/build_logos_research_mobile_shell_hypo_v1.py"]),
        ("sync_public", ["node", "projects/no1kmedi/scripts/sync-logos-studio-data.mjs"]),
        ("pytest_expansion", [PY, "-m", "pytest", "tests/test_logos_studio_preset_expansion_v1.py", "-q"]),
        ("pytest_embedding", [PY, "-m", "pytest", "tests/test_logos_studio_embedding_router_v1.py", "-q"]),
        ("offline_embedding_smoke", [PY, "scripts/check_logos_studio_embedding_router_offline_v1.py"]),
    ]
    for label, cmd in steps:
        if _run(label, cmd) != 0:
            return 1
    out = ROOT / "reports/logos_studio_hd_autonomous_chain_v1_latest.json"
    out.write_text(
        json.dumps(
            {
                "ok": True,
                "schema": "logos_studio_hd_autonomous_chain_v1",
                "reproduce": "py scripts/run_logos_studio_hd_autonomous_chain_v1.py",
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"ok": True, "out": str(out)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
