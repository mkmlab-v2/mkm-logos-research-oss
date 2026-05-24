#!/usr/bin/env python3
"""Phase 2 auto-progress: drafts, queue sync, handoff, Buffer previews — no approve/publish."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/marketing/marketing_auto_phase2_latest.json"
NEXT_MD = ROOT / "reports/marketing/marketing_commander_next_steps_latest.md"

LINKEDIN_IDS = (
    "compression_governance_moat_w12",
    "showroom_topology_observability_ko",
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {
        "cmd": cmd,
        "exit_code": int(proc.returncode),
        "ok": proc.returncode == 0,
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-600:],
    }


def _write_next_steps_md(handoff: dict[str, Any]) -> None:
    post_ready = "reports/marketing/marketing_linkedin_post_ready_latest.md"
    lines = [
        "# Marketing commander next steps (LinkedIn)",
        "",
        f"- **generated_at_utc:** `{_utc()}`",
        "- **recommended:** OpenChrome headed (logged-in Chrome) — agent or `linkedin_openchrome_publish_request_latest.json`",
        "- **fallback:** manual paste from clipboard / `linkedin_paste_primary_latest.txt`",
        f"- **copy from:** `{post_ready}`",
        "",
        "## One-shot prep (PC)",
        "",
        "```powershell",
        "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Invoke-MarketingLinkedInPublishPrep_v1.ps1",
        "```",
        "",
        "## After live post (chat: 올렸어)",
        "",
        "```powershell",
        "py scripts/marketing_linkedin_publish_closure_v1.py --phrase \"올렸어\"",
        "```",
        "",
        "## Per item",
        "",
    ]
    for row in handoff.get("items") or []:
        if not isinstance(row, dict):
            continue
        iid = row.get("id")
        lines.append(f"### `{iid}`")
        lines.append(f"- queue_status: **{row.get('queue_status')}** · copy_guard: **{row.get('copy_guard')}**")
        lines.append(f"- draft: `{row.get('draft_markdown', '—')}`")
        lines.append("1. Open post body in `" + post_ready + "`")
        lines.append("2. Paste into LinkedIn and publish")
        lines.append("3. After live:")
        lines.append("```powershell")
        lines.append(f"py scripts/set_marketing_queue_publish_status_v1.py --item-id {iid} --mark-published")
        lines.append("```")
        lines.append("")
    lines.append(
        "Buffer (`push_marketing_draft_to_buffer_v1.py`) is optional only if you use Buffer with tokens in `.env`."
    )
    NEXT_MD.parent.mkdir(parents=True, exist_ok=True)
    NEXT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output", type=Path, default=OUT)
    ap.add_argument(
        "--auto-approve",
        action="store_true",
        help="drafted + copy_guard PASS items → human_approved (no publish/Buffer push).",
    )
    ap.add_argument(
        "--prep-pc",
        action="store_true",
        help="After exports: clipboard primary + open linkedin.com/feed + emit OpenChrome agent handoff JSON.",
    )
    ap.add_argument(
        "--skip-buffer-preview",
        action="store_true",
        help="Skip Buffer preview for LinkedIn items (e.g. already published).",
    )
    args = ap.parse_args()

    py = sys.executable
    steps: list[dict[str, Any]] = []

    steps.append(_run([py, "scripts/run_marketing_ops_parallel_bundle_v1.py", "--max-workers", "6"]))

    approvals: list[dict[str, Any]] = []
    if args.auto_approve:
        handoff_path = ROOT / "reports/marketing/marketing_publish_handoff_latest.json"
        if handoff_path.is_file():
            ho = json.loads(handoff_path.read_text(encoding="utf-8"))
            for row in ho.get("items") or []:
                if not isinstance(row, dict):
                    continue
                if row.get("copy_guard") != "PASS":
                    continue
                if row.get("queue_status") not in ("drafted", "human_approved"):
                    continue
                iid = str(row.get("id") or "")
                if not iid:
                    continue
                if row.get("queue_status") == "human_approved":
                    approvals.append({"item_id": iid, "skipped": True, "reason": "already_approved"})
                    continue
                approvals.append(
                    {
                        "item_id": iid,
                        **_run(
                            [
                                py,
                                "scripts/set_marketing_queue_publish_status_v1.py",
                                "--item-id",
                                iid,
                                "--approve",
                            ]
                        ),
                    }
                )
        steps.extend(approvals)
        _run([py, "scripts/build_marketing_publish_handoff_v1.py"])

    steps.append(_run([py, "scripts/build_marketing_linkedin_post_ready_v1.py"]))
    steps.append(_run([py, "scripts/build_marketing_linkedin_paste_exports_v1.py"]))

    if args.prep_pc:
        steps.append(
            _run(
                [
                    py,
                    "scripts/publish_marketing_linkedin_feed_prep_v1.py",
                    "--skip-rebuild",
                    "--emit-agent-request",
                ]
            )
        )

    previews: list[dict[str, Any]] = []
    if not args.skip_buffer_preview:
        for iid in LINKEDIN_IDS:
            prev_out = ROOT / "reports/marketing" / f"buffer_push_preview_{iid}_latest.json"
            r = _run(
                [
                    py,
                    "scripts/push_marketing_draft_to_buffer_v1.py",
                    "--item-id",
                    iid,
                    "--out-json",
                    str(prev_out.relative_to(ROOT)).replace("\\", "/"),
                ]
            )
            previews.append({"item_id": iid, **r, "preview_path": str(prev_out.relative_to(ROOT))})
        steps.extend(previews)
    else:
        steps.append({"step": "buffer_preview", "skipped": True, "ok": True})

    handoff_path = ROOT / "reports/marketing/marketing_publish_handoff_latest.json"
    handoff: dict[str, Any] = {}
    if handoff_path.is_file():
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    _write_next_steps_md(handoff)

    doc = {
        "schema": "marketing_auto_phase2_v1",
        "generated_at_utc": _utc(),
        "auto_publish_allowed": False,
        "auto_approve_ran": bool(args.auto_approve),
        "boundary_ack": (
            "MKM scripts do not call LinkedIn API. PC prep + OpenChrome agent publish is supported; "
            "--mark-published via marketing_linkedin_publish_closure_v1.py after live post. "
            "No Buffer --push-draft unless commander runs push separately."
        ),
        "recommended_publish_path": "linkedin_openchrome_headed",
        "steps": steps,
        "all_ok": all(s.get("ok") or s.get("skipped") for s in steps),
        "artifacts": {
            "publish_checklist": "reports/marketing/marketing_publish_checklist_latest.md",
            "commander_next_steps": str(NEXT_MD.relative_to(ROOT)).replace("\\", "/"),
            "parallel_bundle": "reports/marketing/marketing_ops_parallel_bundle_v1_latest.json",
            "linkedin_post_ready": "reports/marketing/marketing_linkedin_post_ready_latest.md",
            "linkedin_paste_primary": "reports/marketing/linkedin_paste_primary_latest.txt",
            "linkedin_paste_exports": "reports/marketing/marketing_linkedin_paste_exports_latest.json",
        },
        "ready_for_human_fire": handoff.get("ready_for_human_fire_count"),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "output": str(args.output), "next_md": str(NEXT_MD)}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
