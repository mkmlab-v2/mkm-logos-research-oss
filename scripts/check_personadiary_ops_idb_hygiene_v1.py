#!/usr/bin/env python3
"""PersonaDiary /ops IndexedDB hygiene — static contract + schema pytest tail."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "projects/no1kmedi/src/lib/personadiaryMobileOpsStore.ts"
HOOK = ROOT / "projects/no1kmedi/src/components/personadiary/usePersonadiaryMobileOps.ts"
OPS_HOME = ROOT / "projects/no1kmedi/src/components/personadiary/PersonadiaryOpsHome.tsx"
OUT = ROOT / "reports/personadiary_ops_idb_hygiene_latest.json"

REQUIRED_MARKERS = (
    "PERSONADIARY_IDB_OPEN_TIMEOUT_MS",
    "PERSONADIARY_IDB_READ_TIMEOUT_MS",
    "idb_open_blocked",
    "default_fallback",
    "db.close()",
    "pd-ops-idb-hygiene-v1",
)


def main() -> int:
    errors: list[str] = []
    store_text = STORE.read_text(encoding="utf-8") if STORE.is_file() else ""
    hook_text = HOOK.read_text(encoding="utf-8") if HOOK.is_file() else ""
    ops_text = OPS_HOME.read_text(encoding="utf-8") if OPS_HOME.is_file() else ""

    for marker in REQUIRED_MARKERS:
        if marker == "db.close()":
            if "db.close()" not in store_text:
                errors.append("missing_db_close")
            continue
        if marker == "pd-ops-idb-hygiene-v1":
            if marker not in ops_text:
                errors.append(f"missing_marker:{marker}")
            continue
        if marker not in store_text and marker not in hook_text:
            errors.append(f"missing_marker:{marker}")

    pytest_cmd = [
        sys.executable,
        "-m",
        "pytest",
        "tests/test_personadiary_mobile_ops_v1_schema.py",
        "tests/test_personadiary_hygiene_prefs_hypo_v1_schema.py",
        "-q",
        "--tb=no",
    ]
    proc = subprocess.run(pytest_cmd, cwd=ROOT, capture_output=True, text=True)
    pytest_ok = proc.returncode == 0

    report = {
        "schema": "personadiary_ops_idb_hygiene_v1",
        "generated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "research_only": True,
        "hypothesis_tier": "B",
        "static_markers_ok": not errors,
        "pytest_ok": pytest_ok,
        "errors": errors,
        "pytest_tail": (proc.stdout or proc.stderr or "").strip()[-400:],
        "ok": not errors and pytest_ok,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
