#!/usr/bin/env python3
"""Integrated LinkedIn marketing: tier15 Gemini regen (optional) → approve → handoff → prep → publish hints."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "reports/marketing/marketing_linkedin_integrated_latest.json"
QUEUE = ROOT / "data/marketing/marketing_content_queue.json"
ENV_PATH = ROOT / ".env"
LINKEDIN_IDS = ("compression_governance_moat_w12", "showroom_topology_observability_ko")
MOAT_ID = "compression_governance_moat_w12"


def _load_dotenv() -> None:
    """Load .env into os.environ (mirror Import-WorkspaceDotEnv_v1.ps1 for child processes)."""
    ps1 = ROOT / "scripts" / "Import-WorkspaceDotEnv_v1.ps1"
    if ps1.is_file():
        subprocess.run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ps1),
                "-WorkspaceRoot",
                str(ROOT),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if not ENV_PATH.is_file():
        return
    for raw in ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key and not os.environ.get(key, "").strip():
            os.environ[key] = val.strip().strip('"').strip("'")


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
        "tail": ((proc.stdout or "") + (proc.stderr or ""))[-500:],
    }


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def _gemini_api_key_present() -> bool:
    return bool(
        os.environ.get("GEMINI_API_KEY", "").strip()
        or os.environ.get("GOOGLE_API_KEY", "").strip()
        or os.environ.get("GOOGLE_AI_STUDIO_API_KEY", "").strip()
    )


def _set_env_flag(name: str, value: str) -> dict[str, Any]:
    if not ENV_PATH.is_file():
        return {"ok": False, "error": ".env missing"}
    lines = ENV_PATH.read_text(encoding="utf-8", errors="replace").splitlines()
    pat = re.compile(rf"^\s*#?\s*{re.escape(name)}\s*=")
    found = False
    for i, line in enumerate(lines):
        if pat.match(line):
            lines[i] = f"{name}={value}"
            found = True
            break
    if not found:
        lines.append(f"{name}={value}")
    ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"ok": True, "name": name, "value": value}


def _reset_linkedin_for_publish(*, exclude_ids: set[str]) -> dict[str, Any]:
    doc = json.loads(QUEUE.read_text(encoding="utf-8"))
    changed: list[str] = []
    for item in doc.get("items") or []:
        if not isinstance(item, dict):
            continue
        iid = str(item.get("id") or "")
        if iid not in LINKEDIN_IDS or iid in exclude_ids:
            continue
        if item.get("status") == "published":
            continue  # keep live-publish SSOT; do not rewind to human_approved
        if item.get("status") in ("drafted", "pending"):
            item["status"] = "human_approved"
            item.pop("published_at_utc", None)
            changed.append(iid)
    if changed:
        doc["updated_at_utc"] = _utc()
        QUEUE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "reset_to_human_approved": changed}


def _all_linkedin_published() -> bool:
    if not QUEUE.is_file():
        return False
    doc = json.loads(QUEUE.read_text(encoding="utf-8"))
    linkedin = [i for i in doc.get("items") or [] if isinstance(i, dict) and i.get("channel") == "linkedin"]
    return bool(linkedin) and all(str(i.get("status")) == "published" for i in linkedin)


def _soft_pass_published_prep(steps: list[dict[str, Any]]) -> None:
    if not _all_linkedin_published():
        return
    for s in steps:
        cmd = " ".join(str(x) for x in (s.get("cmd") or []))
        if "build_marketing_linkedin_post_ready_v1.py" in cmd or "build_marketing_linkedin_paste_exports_v1.py" in cmd:
            if not s.get("ok"):
                s["ok"] = True
                s["soft_pass"] = True
                s["note"] = "LinkedIn already published; reuse linkedin_paste_ready/*_public.txt"


def _approve_drafted_pass() -> list[dict[str, Any]]:
    py = sys.executable
    out: list[dict[str, Any]] = []
    handoff_path = ROOT / "reports/marketing/marketing_publish_handoff_latest.json"
    if not handoff_path.is_file():
        return out
    ho = json.loads(handoff_path.read_text(encoding="utf-8"))
    for row in ho.get("items") or []:
        if not isinstance(row, dict):
            continue
        if row.get("copy_guard") != "PASS" or row.get("queue_status") != "drafted":
            continue
        iid = str(row.get("id") or "")
        if not iid:
            continue
        out.append(
            {
                "item_id": iid,
                **_run(
                    [py, "scripts/set_marketing_queue_publish_status_v1.py", "--item-id", iid, "--approve"]
                ),
            }
        )
    return out


def _queue_reset_for_regen(item_id: str) -> dict[str, Any]:
    doc = json.loads(QUEUE.read_text(encoding="utf-8"))
    for item in doc.get("items") or []:
        if isinstance(item, dict) and item.get("id") == item_id:
            item["status"] = "pending"
            for key in ("published_at_utc", "human_approved_at_utc"):
                item.pop(key, None)
            doc["updated_at_utc"] = _utc()
            QUEUE.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return {"ok": True, "item_id": item_id, "status": "pending"}
    return {"ok": False, "error": f"item not found: {item_id}"}


def _tier15_gemini_regen_moat(*, with_chart: bool) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    if not _gemini_api_key_present():
        steps.append({"step": "gemini_regen", "ok": False, "skipped": True, "reason": "no GEMINI_API_KEY"})
        return steps

    steps.append(_run([sys.executable, "scripts/set_marketing_queue_cost_tier_v1.py", "--active-tier", "tier_15", "--event-week", "--gemini-item", MOAT_ID]))
    steps.append(_queue_reset_for_regen(MOAT_ID))
    steps.append(_set_env_flag("MKM_MARKETING_GEMINI_ALLOWED", "1"))

    gen_cmd = [
        sys.executable,
        "scripts/generate_linkedin_b2b_copy_v1.py",
        "--gemini",
        "--item-id",
        MOAT_ID,
        "--strict-compliance",
    ]
    if with_chart:
        gen_cmd.append("--with-chart")
    steps.append(_run(gen_cmd))
    return steps


def _revert_tier0() -> list[dict[str, Any]]:
    steps = [
        _run(
            [
                sys.executable,
                "scripts/set_marketing_queue_cost_tier_v1.py",
                "--active-tier",
                "tier_0",
                "--clear-event-week",
                "--reset-gemini-flags",
            ]
        ),
        _set_env_flag("MKM_MARKETING_GEMINI_ALLOWED", "0"),
    ]
    return steps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--gemini-regen-moat", action="store_true", help="tier_15 + Gemini regen moat only")
    ap.add_argument("--with-chart", action="store_true", default=True)
    ap.add_argument("--no-chart", action="store_true")
    ap.add_argument(
        "--reset-for-publish",
        action="store_true",
        default=True,
        help="published LinkedIn rows → human_approved (prep pipeline)",
    )
    ap.add_argument("--no-reset-for-publish", action="store_false", dest="reset_for_publish")
    ap.add_argument("--prep-pc", action="store_true", default=True, help="post_ready, paste, clipboard, agent handoff")
    ap.add_argument("--no-prep-pc", action="store_false", dest="prep_pc")
    ap.add_argument("--revert-tier0", action="store_true", default=True)
    ap.add_argument("--skip-revert-tier0", action="store_false", dest="revert_tier0")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    _load_dotenv()
    py = sys.executable
    steps: list[dict[str, Any]] = []
    exclude: set[str] = set()

    if args.gemini_regen_moat:
        gemini_steps = _tier15_gemini_regen_moat(with_chart=not args.no_chart)
        steps.extend(gemini_steps)
        if any(s.get("ok") and s.get("cmd") for s in gemini_steps if isinstance(s, dict)):
            exclude.add(MOAT_ID)

    if args.reset_for_publish:
        steps.append(_reset_linkedin_for_publish(exclude_ids=exclude))

    steps.append(_run([py, "scripts/build_marketing_publish_handoff_v1.py"]))
    steps.extend(_approve_drafted_pass())
    steps.append(_run([py, "scripts/build_marketing_publish_handoff_v1.py"]))

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
    steps.append(
        _run(
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-File",
                str(ROOT / "scripts" / "Invoke-MarketingPublishPhase2_v1.ps1"),
            ]
        )
    )

    if args.revert_tier0 and args.gemini_regen_moat:
        steps.extend(_revert_tier0())

    _soft_pass_published_prep(steps)

    handoff_path = ROOT / "reports/marketing/marketing_publish_handoff_latest.json"
    handoff: dict[str, Any] = {}
    if handoff_path.is_file():
        handoff = json.loads(handoff_path.read_text(encoding="utf-8"))

    pending_publish = [
        {
            "id": row.get("id"),
            "queue_status": row.get("queue_status"),
            "copy_guard": row.get("copy_guard"),
            "public_paste": f"reports/marketing/linkedin_paste_ready/{row.get('id')}_public.txt",
        }
        for row in handoff.get("items") or []
        if isinstance(row, dict) and row.get("copy_guard") == "PASS"
    ]

    doc = {
        "schema": "marketing_linkedin_integrated_v1",
        "generated_at_utc": _utc(),
        "steps": steps,
        "all_ok": all(
            s.get("ok", True)
            or s.get("soft_pass")
            or (s.get("skipped") and s.get("reason") == "no GEMINI_API_KEY")
            for s in steps
            if isinstance(s, dict)
        ),
        "pending_publish": pending_publish,
        "openchrome_publish_order": [MOAT_ID, "showroom_topology_observability_ko"],
        "agent_note": (
            "After this script: use OpenChrome headed — navigate feed, 글 올리기, paste from "
            "*_public.txt per item, 업데이트, then py scripts/marketing_linkedin_publish_closure_v1.py "
            '--phrase "올렸어"'
        ),
        "artifacts": {
            "handoff": "reports/marketing/marketing_publish_handoff_latest.json",
            "checklist": "reports/marketing/marketing_publish_checklist_latest.md",
            "agent_request": "reports/marketing/linkedin_openchrome_publish_request_latest.json",
        },
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["all_ok"], "output": str(args.out_json), "pending": len(pending_publish)}, ensure_ascii=False))
    return 0 if doc["all_ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
