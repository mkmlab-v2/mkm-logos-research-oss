#!/usr/bin/env python3
"""Gate: Logos Research commercial hardening files + public data sync."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1K = ROOT / "projects" / "no1kmedi"
DATA = NO1K / "public" / "data" / "logos_studio"
OUT = ROOT / "reports" / "logos_research_commercial_hardening_gate_v1_latest.json"

REQUIRED = [
    NO1K / "src" / "app" / "logos-research" / "studio" / "page.tsx",
    NO1K / "src" / "app" / "api" / "logos-research" / "query" / "route.ts",
    NO1K / "src" / "app" / "api" / "logos-research" / "presets" / "route.ts",
    NO1K / "src" / "app" / "api" / "logos-research" / "lead" / "route.ts",
    NO1K / "src" / "components" / "logos-research" / "LogosResearchSubgraphPanel.tsx",
    NO1K / "src" / "components" / "logos-research" / "LogosResearchSubgraphViz.tsx",
    NO1K / "src" / "lib" / "logosResearchForceGraphV1.ts",
    NO1K / "src" / "lib" / "logosResearchGraphLayoutV1.ts",
    NO1K / "src" / "components" / "logos-research" / "LogosResearchStudioClient.tsx",
    NO1K / "scripts" / "sync-logos-studio-data.mjs",
]

DATA_FILES = [
    DATA / "qa_presets_v1.json",
    DATA / "qa_router_sidecar_v1.json",
    DATA / "graph_slice_v1.json",
]


def main() -> int:
    missing = [str(p.relative_to(ROOT)) for p in REQUIRED if not p.is_file()]
    data_missing = [str(p.relative_to(ROOT)) for p in DATA_FILES if not p.is_file()]

    sync_exit = None
    if data_missing:
        proc = subprocess.run(
            ["node", str(NO1K / "scripts" / "sync-logos-studio-data.mjs")],
            cwd=str(NO1K),
            capture_output=True,
            text=True,
        )
        sync_exit = proc.returncode
        data_missing = [str(p.relative_to(ROOT)) for p in DATA_FILES if not p.is_file()]

    ok = not missing and not data_missing and (sync_exit in (None, 0))
    payload = {
        "schema": "logos_research_commercial_hardening_gate_v1",
        "ok": ok,
        "missing": missing,
        "data_missing": data_missing,
        "sync_exit": sync_exit,
        "studio_path": "/logos-research/studio",
        "reproduce": "py scripts/check_logos_research_commercial_hardening_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
