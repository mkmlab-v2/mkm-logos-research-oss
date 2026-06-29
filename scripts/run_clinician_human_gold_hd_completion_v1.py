#!/usr/bin/env python3
"""HD tier_0 completion artifact — Human Gold clinician deliverables chain v0."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "hd_autonomous_evolution_completion_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], cwd: Path) -> int:
    p = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True)
    if p.returncode != 0:
        sys.stderr.write((p.stderr or p.stdout or "")[:2000])
    return int(p.returncode)


def main() -> int:
    steps: dict[str, dict] = {}
    ok = True

    for name, rel in [
        ("encounter_artifacts_offline", "projects/no1kmedi/scripts/smoke-clinician-encounter-artifacts-offline.mjs"),
        ("intake_fusion_offline", "projects/no1kmedi/scripts/smoke-clinician-intake-fusion-draft-offline.mjs"),
        ("paste_chart_offline", "projects/no1kmedi/scripts/smoke-clinician-paste-chart-offline.mjs"),
        ("lifestyle_deliverables_offline", "projects/no1kmedi/scripts/smoke-clinician-encounter-lifestyle-deliverables-offline.mjs"),
    ]:
        script = ROOT / rel
        code = _run(["node", str(script)], ROOT)
        steps[name] = {"exit_code": code, "ok": code == 0}
        if code != 0:
            ok = False

    doc = {
        "schema": "hd_autonomous_evolution_completion_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tag": "[HYPO]",
        "research_only": True,
        "mission_line": "Paste Chart v1: EMR paste → SOAP + advice (/clinician Paste Chart)",
        "cost_tier": "tier_0",
        "lane": "design",
        "quality_pass": 1,
        "max_quality_passes": 1,
        "quality_ok": ok,
        "preflight_note": "Invoke-MkmHighDelegationPreflight_v1 M/design: host_ready=false (browser); tier_0 local chains proceeded",
        "completion_contract": {
            "exit_code_target": 0,
            "artifact": "reports/hd_autonomous_evolution_completion_v1_latest.json",
            "reproducible_command": "py scripts/run_clinician_human_gold_hd_completion_v1.py",
        },
        "steps": steps,
        "artifacts": {
            "preflight": "reports/mkm_high_delegation_preflight_v1_latest.json",
            "encounter_artifacts_api": "projects/no1kmedi/src/app/api/clinician/encounter-artifacts/route.ts",
            "intake_fusion_api": "projects/no1kmedi/src/app/api/clinician/intake-fusion-draft-v1/route.ts",
            "paste_chart_api": "projects/no1kmedi/src/app/api/clinician/paste-chart-v1/route.ts",
            "lifestyle_deliverables_api": "projects/no1kmedi/src/app/api/clinician/encounter-lifestyle-deliverables-v1/route.ts",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
