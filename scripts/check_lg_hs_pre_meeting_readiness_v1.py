#!/usr/bin/env python3
"""LG HS 5/20 pre-meeting gate: B2B pack + deck + followup pointers (local files only)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/lg_hs_pre_meeting_readiness_v1_latest.json"
FOLLOWUP = ROOT / "docs/final/artifacts/lg_hs_meeting_followup_v1.json"
DECK = ROOT / "docs/final/artifacts/lg_hs_compression_discipline_deck_v1_latest.md"
PACK_INDEX = ROOT / "docs/final/artifacts/track_c_b2b_meeting_pack_index_v1_latest.md"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT)
    args = ap.parse_args()

    checks: list[dict] = []
    for label, path in (
        ("followup_json", FOLLOWUP),
        ("deck_md", DECK),
        ("b2b_pack_index", PACK_INDEX),
    ):
        checks.append({"id": f"file:{path.name}", "ok": path.is_file(), "path": str(path.relative_to(ROOT))})

    track_c_ok = False
    track_c_path = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts/check_track_c_b2b_meeting_pack_readiness_v1.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if cp.returncode == 0 and track_c_path.is_file():
        tc = json.loads(track_c_path.read_text(encoding="utf-8"))
        track_c_ok = bool(tc.get("ready_for_internal_meeting"))
        checks.append({"id": "track_c_internal_meeting", "ok": track_c_ok})

    pre = {}
    if FOLLOWUP.is_file():
        fu = json.loads(FOLLOWUP.read_text(encoding="utf-8"))
        pre = fu.get("pre_meeting_2026_05_20") if isinstance(fu.get("pre_meeting_2026_05_20"), dict) else {}

    ready = all(c.get("ok") for c in checks)
    doc = {
        "schema": "lg_hs_pre_meeting_readiness_v1",
        "generated_at_utc": _utc_now(),
        "ready_for_internal_meeting": ready and track_c_ok,
        "external_send_allowed": False,
        "checks": checks,
        "pre_meeting_pointer": pre,
        "note": "Deck + pack are internal-only until legal sign-off on external surfaces.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ready and track_c_ok, "output": str(args.output)}, ensure_ascii=False))
    return 0 if ready and track_c_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
