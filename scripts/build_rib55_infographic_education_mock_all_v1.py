#!/usr/bin/env python3
"""Build education HTML mocks for all rib55 manifest entries."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "docs/final/artifacts/rib55_angle_overlay_manifest_v1.json"
BUILDER = ROOT / "scripts/build_rib55_infographic_education_mock_v1.py"
OUT_INDEX = ROOT / "reports/rib55_infographic_education_mock_index_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main() -> int:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows: list[dict] = []
    for entry in manifest.get("entries") or []:
        eid = str(entry.get("entry_id"))
        out = ROOT / "reports/demo" / f"rib55_infographic_education_{eid}_v1.html"
        proc = subprocess.run(
            [sys.executable, str(BUILDER), "--entry-id", eid, "--out", str(out)],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        rows.append({"entry_id": eid, "out": str(out.relative_to(ROOT)).replace("\\", "/"), "exit_code": proc.returncode})
        if proc.returncode != 0:
            print(proc.stderr or proc.stdout, file=sys.stderr)
            break

    ok = all(r["exit_code"] == 0 for r in rows)
    doc = {
        "schema": "rib55_infographic_education_mock_index_v1",
        "generated_at_utc": _utc(),
        "entries": rows,
        "ok": ok,
        "reproduce": "py scripts/build_rib55_infographic_education_mock_all_v1.py",
    }
    OUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_INDEX.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "count": len(rows)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
