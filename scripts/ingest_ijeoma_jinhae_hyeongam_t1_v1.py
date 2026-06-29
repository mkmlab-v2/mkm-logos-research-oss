#!/usr/bin/env python3
"""Ingest Jinhae hyeongam T1 career proxy + fragment mine."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROXY = ROOT / "docs/research/raw/IJEOMA_JINHAE_HYEONGAM_career_T1_nl_proxy.md"
OUT = ROOT / "reports/constitution/btrack_pilot/ijeoma_jinhae_hyeongam_t1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not PROXY.is_file():
        print(json.dumps({"ok": False, "error": f"missing: {PROXY}"}))
        return 1
    text = PROXY.read_text(encoding="utf-8")
    for needle in ("진해현감", "1886", "1889", "cheonyucho_primary"):
        if needle not in text:
            print(json.dumps({"ok": False, "error": f"missing needle: {needle}"}))
            return 1

    cp = subprocess.run(
        [sys.executable, "scripts/run_cheonyucho_fragment_mine_v1.py"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    tail = (cp.stdout or cp.stderr or "").strip().splitlines()
    line = tail[-1] if tail else "{}"
    try:
        mine = json.loads(line)
    except json.JSONDecodeError:
        mine = {"raw_tail": line}

    doc = {
        "schema": "ijeoma_jinhae_hyeongam_t1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "tier": "T1_secondary_bibliographic",
        "proxy": PROXY.relative_to(ROOT).as_posix(),
        "ssot_primary": "encykorea E0045869",
        "appointed_utc_gregorian": "1886",
        "took_office": "1887-02",
        "retired": "1889-12",
        "alternate_unresolved": ["AKS people 1893-07 resign", "wikipedia 1887 resign"],
        "cheonyucho_primary": False,
        "fragment_mine_exit_code": cp.returncode,
        "fragment_mine": mine,
        "reproduce": "py scripts/ingest_ijeoma_jinhae_hyeongam_t1_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": cp.returncode == 0, "out": str(OUT)}))
    return 0 if cp.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
