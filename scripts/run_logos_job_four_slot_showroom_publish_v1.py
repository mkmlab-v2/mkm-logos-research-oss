#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Job four-slot showroom publish — UTF-8 safe chain + optional deploy/KV hooks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
FIXTURE = ROOT / "docs/final/fixtures/magic_orb_question_insight_queries_v1.json"
JOB_HASH = "dc73c2c367199e48"
JOB_PUBLIC = ROOT / f"projects/mkm/mkm-life/public/data/magic_orb_insight_by_query/{JOB_HASH}.json"
OUT = ROOT / "reports/logos_job_four_slot_showroom_publish_v1_latest.json"


def _job_query() -> str:
    doc = json.loads(FIXTURE.read_text(encoding="utf-8"))
    for item in doc.get("items") or []:
        if item.get("id") == "job_suffering_reason":
            return str(item["query_ko"])
    raise SystemExit("fixture missing job_suffering_reason")


def _run(cmd: list[str], *, dry_run: bool = False, cwd: Path | None = None) -> int:
    print("+", " ".join(cmd), flush=True)
    if dry_run:
        return 0
    return subprocess.call(cmd, cwd=str(cwd or ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description="Publish job four-slot insight to by-query + live.")
    ap.add_argument("--skip-chain", action="store_true")
    ap.add_argument("--skip-deploy", action="store_true")
    ap.add_argument("--skip-kv", action="store_true")
    ap.add_argument("--skip-smoke", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--with-post-llm-fill",
        action="store_true",
        help="Run template_expand post-LLM fill after bridge chain gate",
    )
    args = ap.parse_args()

    query = _job_query()
    steps: dict = {}

    if not args.skip_chain:
        chain_cmd = [
            PY,
            str(ROOT / "scripts/run_question_semantic_rag_bridge_chain_v1.py"),
            "--query",
            query,
            "--query-id",
            "job_suffering_reason",
            "--skip-ann-lite",
            "--expand-graph",
            "--sync-public",
            "--sync-public-by-query",
        ]
        if args.with_post_llm_fill:
            chain_cmd.append("--with-post-llm-fill")
        rc = _run(chain_cmd, dry_run=args.dry_run)
        steps["chain"] = {"ok": rc == 0, "exit_code": rc}
        if rc != 0:
            return rc

    if not JOB_PUBLIC.is_file() and not args.dry_run:
        print(json.dumps({"ok": False, "error": "missing_job_by_query_public", "path": str(JOB_PUBLIC)}))
        return 1

    if not args.skip_deploy:
        rc = _run([PY, str(ROOT / "scripts/build_magic_orb_query_presets_from_fixture_v1.py")], dry_run=args.dry_run)
        steps["preset_codegen"] = {"ok": rc == 0, "exit_code": rc}
        if rc != 0:
            return rc
        rc = _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "projects/mkm/mkm-life/scripts/Deploy-CloudflareMkmlife.ps1"),
                "-SkipOracleSphereHero",
            ],
            dry_run=args.dry_run,
        )
        steps["deploy"] = {"ok": rc == 0, "exit_code": rc}
        if rc != 0:
            return rc

    if not args.skip_kv:
        kv_cmd = [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(ROOT / "scripts/Invoke-MkmlifeMagicOrbInsightKvPush_v1.ps1"),
            "-WranglerDirect",
        ]
        if args.dry_run:
            kv_cmd.append("-DryRun")
        rc = _run(kv_cmd, dry_run=False)
        steps["kv_push"] = {"ok": rc == 0, "exit_code": rc}
        if rc != 0:
            return rc

    if not args.skip_smoke:
        rc = _run(
            [PY, str(ROOT / "scripts/probe_mkmlife_magic_orb_job_four_slot_live_v1.py")],
            dry_run=args.dry_run,
        )
        steps["probe_job"] = {"ok": rc == 0, "exit_code": rc}
        if rc != 0:
            return rc
        rc = _run(
            [PY, str(ROOT / "scripts/probe_mkmlife_magic_orb_live_v1.py"), "--profile", "core"],
            dry_run=args.dry_run,
        )
        steps["probe_core"] = {"ok": rc == 0, "exit_code": rc, "note": "core tier gate for oracle-sphere ops"}
        if rc != 0:
            return rc
        rc = _run(
            [
                "npm",
                "run",
                "smoke:magic-orb-oracle-preset-playwright",
            ],
            dry_run=args.dry_run,
            cwd=ROOT / "projects/mkm/mkm-life",
        )
        steps["playwright_preset_e2e"] = {
            "ok": rc == 0,
            "exit_code": rc,
            "note": "optional strict: MKM_SMOKE_STRICT_PLAYWRIGHT=1",
        }

    doc = {
        "schema": "logos_job_four_slot_showroom_publish_v1",
        "ok": True,
        "query_id": "job_suffering_reason",
        "query_key_hash": JOB_HASH,
        "public_by_query": str(JOB_PUBLIC.relative_to(ROOT)).replace("\\", "/"),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "send_gate": "HOLD",
        "steps": steps,
        "reproducible_command": "py scripts/run_logos_job_four_slot_showroom_publish_v1.py",
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(doc, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
