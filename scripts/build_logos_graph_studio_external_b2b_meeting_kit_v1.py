#!/usr/bin/env python3
"""Assemble first external B2B meeting kit index (human-send only · SEND_GATE HOLD)."""

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
OUT_JSON = ROOT / "reports/logos_graph_studio_external_b2b_meeting_kit_v1_latest.json"
OUT_MD = ROOT / "docs/final/artifacts/logos_graph_studio_external_b2b_meeting_kit_v1_latest.md"

POINTERS = [
    ("30s demo script", "docs/final/artifacts/logos_graph_studio_b2b_30s_demo_script_v1_latest.md"),
    ("Meeting pack index", "docs/final/artifacts/logos_graph_studio_b2b_meeting_pack_index_v1_latest.md"),
    ("Live rehearsal checklist", "docs/final/artifacts/logos_graph_studio_b2b_live_rehearsal_checklist_v1_latest.md"),
    ("SOW exec summary", "docs/final/artifacts/logos_graph_studio_pilot_sow_executive_summary_v1_latest.md"),
    ("Pilot SOW template", "docs/final/artifacts/logos_graph_studio_pilot_sow_template_v1_latest.md"),
    ("Organic 1:1 outreach", "docs/final/artifacts/logos_graph_studio_organic_b2b_outreach_v1_latest.md"),
    ("Counsel handoff brief", "docs/final/artifacts/logos_gtm_counsel_handoff_brief_v1_latest.md"),
    ("Signoff worksheet", "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json"),
]

CHAIN_STEPS = [
    "scripts/build_logos_graph_studio_b2b_meeting_pack_v1.py",
    "scripts/build_logos_gtm_counsel_handoff_bundle_v1.py",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str) -> dict[str, Any]:
    proc = subprocess.run([PY, str(ROOT / script)], cwd=ROOT, capture_output=True, text=True)
    return {
        "script": script,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout": (proc.stdout or "").strip()[-400:],
        "stderr": (proc.stderr or "").strip()[-200:],
    }


def _exists(rel: str) -> bool:
    return (ROOT / rel.replace("/", "\\")).is_file()


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-chain", action="store_true")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    if not args.skip_chain:
        for script in CHAIN_STEPS:
            step = _run(script)
            step["id"] = script.split("/")[-1].replace(".py", "")
            steps.append(step)
            if not step["ok"]:
                print(json.dumps({"ok": False, "failed": script}), file=sys.stderr)
                return 1

    missing = [rel for _, rel in POINTERS if not _exists(rel)]
    counsel_bundle = ROOT / "reports/logos_gtm_counsel_handoff_bundle_v1_latest.json"
    counsel_ok = False
    if counsel_bundle.is_file():
        bundle = json.loads(counsel_bundle.read_text(encoding="utf-8-sig"))
        counsel_ok = bool(bundle.get("ready_for_counsel_submission"))

    ready_human = not missing and counsel_ok

    doc = {
        "schema": "logos_graph_studio_external_b2b_meeting_kit_v1",
        "generated_at_utc": _utc(),
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "ready_for_human_first_external_meeting": ready_human,
        "counsel_signoff_required_before_send": True,
        "demo_primary_url": (
            "https://api.jemaai.cloud/public_showroom_meaning_topology_qa_v2.html"
            "?preset=job_job_suffering_reason"
        ),
        "workspace_url": "https://logos.jema-ai.com/logos-research",
        "public_docs_url": "https://logos.jema-ai.com/logos-research/docs",
        "artifact_pointers": {label: path for label, path in POINTERS},
        "missing_artifacts": missing,
        "chain_steps": steps,
        "human_checklist_ko": [
            "counsel handoff brief 전달 + signoff worksheet 초안 공유",
            "30s demo + meeting pack index로 15분 리허설",
            "organic outreach Variant A로 1:1 초대 (human-sent only)",
            "미팅 후 record_logos_graph_studio_pilot_session (external attendees)",
        ],
        "reproduce": "py scripts/build_logos_graph_studio_external_b2b_meeting_kit_v1.py",
    }

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    OUT_JSON.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    md_lines = [
        "# Logos Graph Studio — External B2B Meeting Kit (v1)",
        "",
        f"- **generated_at_utc:** {_utc()}",
        "- **send_gate:** `HOLD` · **ready_for_external_send:** `false`",
        f"- **ready_for_human_first_external_meeting:** `{str(ready_human).lower()}`",
        "",
        "## Live URLs",
        "",
        f"- Demo: {doc['demo_primary_url']}",
        f"- Workspace: {doc['workspace_url']}",
        f"- Docs: {doc['public_docs_url']}",
        "",
        "## Artifacts",
        "",
    ]
    for label, path in POINTERS:
        flag = "OK" if _exists(path) else "MISSING"
        md_lines.append(f"- [{flag}] **{label}** — `{path}`")
    md_lines.extend(
        [
            "",
            "## Human checklist",
            "",
        ]
    )
    for item in doc["human_checklist_ko"]:
        md_lines.append(f"1. {item}")
    md_lines.append("")
    md_lines.append("## Reproduce")
    md_lines.append("")
    md_lines.append("```powershell")
    md_lines.append("py scripts/build_logos_graph_studio_external_b2b_meeting_kit_v1.py")
    md_lines.append("```")
    md_lines.append("")

    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text("\n".join(md_lines), encoding="utf-8")

    print(json.dumps({"ok": ready_human, "out": str(OUT_JSON), "missing": len(missing)}))
    return 0 if ready_human else 1


if __name__ == "__main__":
    raise SystemExit(main())
