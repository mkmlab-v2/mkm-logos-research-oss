#!/usr/bin/env python3
"""Assemble Logos Graph Studio internal B2B meeting pack index + run readiness smokes."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT_INDEX = ROOT / "docs/final/artifacts/logos_graph_studio_b2b_meeting_pack_index_v1_latest.md"
OUT_RUN = ROOT / "reports/logos_graph_studio_b2b_meeting_pack_build_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _exists(rel: str) -> bool:
    return (ROOT / rel).is_file()


def _run_step(name: str, script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [PY, str(ROOT / script), *(extra or [])]
    print("+", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "name": name,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "")[-400:],
        "stderr_tail": (proc.stderr or "")[-200:],
    }


def _build_index(*, generated_at: str, steps: list[dict[str, Any]], readiness_ok: bool) -> str:
    artifacts = [
        ("0 · Commander approval", "docs/final/artifacts/logos_graph_studio_commander_pilot_approval_v1_latest.json"),
        ("1 · PoC one-pager (email attach)", "docs/final/artifacts/logos_graph_studio_b2b_poc_one_pager_v1_latest.md"),
        ("2 · SOW exec summary (1p)", "docs/final/artifacts/logos_graph_studio_pilot_sow_executive_summary_v1_latest.md"),
        ("3 · Pilot SOW template", "docs/final/artifacts/logos_graph_studio_pilot_sow_template_v1_latest.md"),
        ("4 · 30s demo script", "docs/final/artifacts/logos_graph_studio_b2b_30s_demo_script_v1_latest.md"),
        ("5 · Live rehearsal checklist", "docs/final/artifacts/logos_graph_studio_b2b_live_rehearsal_checklist_v1_latest.md"),
        ("5b · GTM LinkedIn/B2B copy variants", "docs/final/artifacts/logos_gtm_linkedin_b2b_copy_variants_v1_latest.md"),
        ("5c · Counsel handoff brief", "docs/final/artifacts/logos_gtm_counsel_handoff_brief_v1_latest.md"),
        ("5d · Organic B2B outreach (1:1)", "docs/final/artifacts/logos_graph_studio_organic_b2b_outreach_v1_latest.md"),
        ("6 · Commercial SKU draft", "docs/final/artifacts/logos_graph_studio_commercial_sku_draft_v1_latest.md"),
        ("7 · URL SSOT", "docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json"),
    ]
    rows = []
    for label, path in artifacts:
        rows.append(f"| {label} | `{path}` | {'OK' if _exists(path) else 'MISSING'} |")

    step_lines = "\n".join(
        f"- `{s['name']}` → exit {s['exit_code']}" + (" OK" if s.get("ok") else " FAIL")
        for s in steps
    )

    return f"""# Logos Graph Studio — Internal B2B Meeting Pack Index (v1)

- **generated_at_utc:** `{generated_at}`
- **status:** `COMMANDER_APPROVED_INTERNAL` · **send_gate:** `HOLD`
- **ready_for_internal_b2b_meeting:** `{str(readiness_ok).lower()}`
- **ready_for_external_send:** `false` (counsel sign-off required)

## Reading order (30 min meeting)

1. **Open (2 min)** — PoC one-pager 한 줄 가치 + 면책 구두 1문장
2. **Live demo (5 min)** — 30s script → QA v2 primary URL (laptop projection)
3. **Scope (10 min)** — SOW exec summary → full SOW template (preset·slice·SLA)
4. **Commercial (5 min)** — logos.jema-ai.com tiers · SKU draft (billing TBD)
5. **Close (3 min)** — pilot timeline · evidence pointers · next counsel gate

## Live URLs

| Surface | URL |
|---------|-----|
| **Graph Studio demo** | https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html?preset=job_job_suffering_reason |
| **Commercial landing** | https://logos.jema-ai.com/logos-research |
| **Public docs** | https://logos.jema-ai.com/logos-research/docs |
| Job Reading Pack | https://api.jemaai.cloud/public_showroom_logos_job_reading_pack_v1.html?preset=job_suffering_reason |

## Build steps (this run)

{step_lines}

## Artifacts

| Step | Path | Disk |
|------|------|------|
{chr(10).join(rows)}

## Evidence (exit 0)

| Report | Path |
|--------|------|
| B2B live rehearsal | `reports/logos_graph_studio_b2b_rehearsal_live_v1_latest.json` |
| logos.jema-ai.com deploy | `reports/logos_jema_ai_deploy_verify_latest.json` |
| Meeting pack readiness | `reports/logos_graph_studio_b2b_meeting_pack_readiness_v1_latest.json` |
| Counsel handoff bundle | `reports/logos_gtm_counsel_handoff_bundle_v1_latest.json` |

## Regenerate

```powershell
py scripts/build_logos_graph_studio_b2b_meeting_pack_v1.py
```

## Disclaimers (every deck · email footer)

> Not investment advice. `[HYPO]` research demo only. `[NON_GATING]`. `send_gate: HOLD`. No buy/sell or live-trading triggers. `ready_for_external_send: false`.
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-live-smoke", action="store_true", help="Skip HTTP rehearsal checks.")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    steps.append(_run_step("product_metrics", "scripts/build_logos_research_product_metrics_v1.py"))
    steps.append(_run_step("showroom_urls", "scripts/build_jemaai_showroom_public_urls_v1.py"))

    steps.append(_run_step("gtm_copy_scan", "scripts/check_logos_gtm_linkedin_b2b_copy_scan_v1.py"))
    steps.append(_run_step("public_docs_copy_scan", "scripts/check_logos_research_public_docs_copy_v1.py"))
    steps.append(_run_step("counsel_handoff_bundle", "scripts/build_logos_gtm_counsel_handoff_bundle_v1.py"))

    if not args.skip_live_smoke:
        steps.append(_run_step("b2b_rehearsal_live", "scripts/check_logos_graph_studio_b2b_rehearsal_live_v1.py"))

    readiness_step = _run_step(
        "meeting_pack_readiness",
        "scripts/check_logos_graph_studio_b2b_meeting_pack_readiness_v1.py",
    )
    steps.append(readiness_step)

    readiness_ok = readiness_step.get("ok", False)
    generated_at = _utc()
    OUT_INDEX.parent.mkdir(parents=True, exist_ok=True)
    OUT_INDEX.write_text(
        _build_index(generated_at=generated_at, steps=steps, readiness_ok=readiness_ok),
        encoding="utf-8",
        newline="\n",
    )
    print(f"WROTE: {OUT_INDEX}")

    run_doc = {
        "schema": "logos_graph_studio_b2b_meeting_pack_build_v1",
        "generated_at_utc": generated_at,
        "ok": all(s.get("ok") for s in steps),
        "readiness_ok": readiness_ok,
        "steps": steps,
        "index": str(OUT_INDEX.relative_to(ROOT)),
        "reproduce": "py scripts/build_logos_graph_studio_b2b_meeting_pack_v1.py",
    }
    OUT_RUN.parent.mkdir(parents=True, exist_ok=True)
    OUT_RUN.write_text(json.dumps(run_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": run_doc["ok"], "out": str(OUT_RUN)}, ensure_ascii=False))
    return 0 if run_doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
