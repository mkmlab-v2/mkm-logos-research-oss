#!/usr/bin/env python3
"""Verify JEONG_YONGJAE T1 digest proxy exists and run fragment mine."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROXY = ROOT / "docs/research/raw/JEONG_YONGJAE_ijoeoma_human_2022_youtube_nl_proxy.md"
OUT = ROOT / "reports/constitution/btrack_pilot/jeong_yongjae_ijoeoma_secondary_digest_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    if not PROXY.is_file():
        print(json.dumps({"ok": False, "error": f"missing proxy: {PROXY}"}))
        return 1
    text = PROXY.read_text(encoding="utf-8")
    if "cheonyucho_primary" not in text or "**false**" not in text:
        print(json.dumps({"ok": False, "error": "must deny cheonyucho_primary"}))
        return 1
    if "박대식" not in text or "박석언" not in text:
        print(json.dumps({"ok": False, "error": "biblio distinction missing"}))
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
        "schema": "jeong_yongjae_ijoeoma_secondary_digest_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "track": "B",
        "send_gate": "HOLD",
        "tier": "T1_secondary_popularization",
        "proxy": PROXY.relative_to(ROOT).as_posix(),
        "cheonyucho_primary_absorbed": False,
        "hanja_canon_status": "not_acquired",
        "absorbed_topics": [
            "geukchigo_dssbw_reading_order",
            "geukchigo_chronology_T1",
            "park_daesik_kr_translation_vs_park_seogeon_1985",
            "ijeoma_career_T1",
        ],
        "fragment_mine_exit_code": cp.returncode,
        "fragment_mine": mine,
        "reproduce": "py scripts/ingest_jeong_yongjae_ijoeoma_secondary_digest_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": cp.returncode == 0, "out": str(OUT), "proxy": str(PROXY)}))
    return 0 if cp.returncode == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
