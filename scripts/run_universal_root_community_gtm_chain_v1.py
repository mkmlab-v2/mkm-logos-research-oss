#!/usr/bin/env python3
"""Universal Root community GTM AUTO chain — smoke evidence · poll · paste verify [HYPO · HOLD]."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.universal_root_gtm_freeze_lib_v1 import evaluate_gtm_freeze  # noqa: E402

OUT = ROOT / "reports/universal_root_community_gtm_chain_v1_latest.json"
GTM = ROOT / "reports/universal_root_community_gtm_v1_latest.json"
PASTE_DIR = ROOT / "reports/human_paste"

REQUIRED_PASTE = [
    "universal_root_x_post_2.txt",
    "universal_root_x_post_3.txt",
    "universal_root_x_post_4.txt",
    "universal_root_smoke_terminal_evidence.png",
    "universal_root_discussions_thread_a_bump.md",
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, cwd: Path | None = None) -> dict[str, Any]:
    proc = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    tail = (proc.stdout or proc.stderr or "").strip().splitlines()
    return {
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "tail": tail[-3:] if tail else [],
    }


def _verify_paste_files() -> dict[str, Any]:
    missing = [name for name in REQUIRED_PASTE if not (PASTE_DIR / name).is_file()]
    return {"ok": not missing, "missing": missing, "dir": str(PASTE_DIR).replace("\\", "/")}


def main() -> int:
    import argparse

    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-capture", action="store_true")
    ap.add_argument("--skip-poll", action="store_true")
    ap.add_argument("--skip-x-semi-auto", action="store_true", help="skip clipboard prep (SkipBrowser)")
    ap.add_argument(
        "--post-discussions-repro",
        action="store_true",
        help="Post maintainer repro reply to Discussions #2 via gh graphql (requires gh auth)",
    )
    ap.add_argument("--discussions-dry-run", action="store_true")
    ap.add_argument(
        "--post-x-api",
        action="store_true",
        help="Post X 2-4 via official API (requires MKM_X_* OAuth keys + --acknowledge-send)",
    )
    ap.add_argument(
        "--acknowledge-send",
        action="store_true",
        help="R4 ack for live X API submit (send_gate HOLD)",
    )
    ap.add_argument(
        "--commander-override-freeze",
        action="store_true",
        help="Bypass GTM FREEZE for --post-discussions-repro live post",
    )
    args = ap.parse_args()

    freeze_ev = evaluate_gtm_freeze(action="read_only")
    steps: dict[str, Any] = {"gtm_freeze_eval": freeze_ev}
    ok = True

    steps["paste_verify"] = _verify_paste_files()
    ok = ok and steps["paste_verify"]["ok"]

    if not args.skip_capture:
        steps["smoke_evidence_capture"] = _run(
            [sys.executable, str(ROOT / "scripts/capture_universal_root_smoke_evidence_v1.py")]
        )
        ok = ok and steps["smoke_evidence_capture"]["ok"]
    else:
        steps["smoke_evidence_capture"] = {"ok": True, "skipped": True}

    if not args.skip_poll:
        steps["community_poll"] = _run(
            [sys.executable, str(ROOT / "scripts/poll_universal_root_community_gtm_v1.py")]
        )
        # poll may fail without gh auth — non-fatal for local paste prep
        if not steps["community_poll"]["ok"]:
            steps["community_poll"]["non_fatal"] = True
    else:
        steps["community_poll"] = {"ok": True, "skipped": True}

    if not args.skip_x_semi_auto:
        ps1 = ROOT / "scripts/Invoke-UniversalRootXPostsSemiAuto_v1.ps1"
        if ps1.is_file():
            steps["x_semi_auto_clipboard"] = _run(
                [
                    "powershell",
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(ps1),
                    "-Post",
                    "all",
                    "-SkipBrowser",
                    "-SkipEvidenceCapture",
                    "-NonInteractive",
                ]
            )
            # clipboard step always exit 0 if files exist — non-blocking for AUTO
            steps["x_semi_auto_clipboard"]["note"] = "clipboard_only · commander posts manually in Chrome"
        else:
            steps["x_semi_auto_clipboard"] = {"ok": False, "error": "ps1_missing"}
    else:
        steps["x_semi_auto_clipboard"] = {"ok": True, "skipped": True}

    if args.post_discussions_repro:
        live_post = not args.discussions_dry_run
        if live_post:
            post_ev = evaluate_gtm_freeze(
                action="discussions_live_post",
                commander_override=args.commander_override_freeze,
            )
            if not post_ev.get("ok"):
                steps["discussions_repro_post"] = {
                    "ok": False,
                    "skipped": True,
                    "blocked": "gtm_freeze",
                    "violations": post_ev.get("violations"),
                }
                ok = False
            else:
                live_post = True
        if steps.get("discussions_repro_post") is None:
            disc_cmd = [
                sys.executable,
                str(ROOT / "scripts/post_universal_root_discussions_bump_v1.py"),
                "--body-file",
                "reports/human_paste/universal_root_discussions_thread_a_repro_reply.md",
            ]
            if args.discussions_dry_run:
                disc_cmd.append("--dry-run")
            elif args.commander_override_freeze:
                disc_cmd.append("--commander-override-freeze")
            steps["discussions_repro_post"] = _run(disc_cmd)
            ok = ok and steps["discussions_repro_post"]["ok"]
    else:
        steps["discussions_repro_post"] = {"ok": True, "skipped": True}

    if args.post_x_api:
        x_cmd = [
            sys.executable,
            str(ROOT / "scripts/post_x_api_v1.py"),
            "--posts",
            "2,3,4",
        ]
        if args.acknowledge_send:
            x_cmd.append("--acknowledge-send")
        else:
            x_cmd.extend(["--dry-run", "--verify-auth"])
        steps["x_api_post"] = _run(x_cmd)
        if args.acknowledge_send:
            ok = ok and steps["x_api_post"]["ok"]
        elif not steps["x_api_post"]["ok"]:
            steps["x_api_post"]["non_fatal"] = True
    else:
        steps["x_api_post"] = {"ok": True, "skipped": True}

    steps["reddit_praw_dry_run"] = _run(
        [sys.executable, str(ROOT / "scripts/post_reddit_praw_v1.py"), "--dry-run", "--pack", "universal_root"]
    )
    if not steps["reddit_praw_dry_run"]["ok"]:
        steps["reddit_praw_dry_run"]["non_fatal"] = True
        steps["reddit_praw_dry_run"]["note"] = "reddit already posted manually or DPAPI creds missing"

    steps["discussions_thread_b_dry_run"] = _run(
        [sys.executable, str(ROOT / "scripts/post_universal_root_discussions_thread_b_v1.py"), "--dry-run"]
    )
    if not steps["discussions_thread_b_dry_run"]["ok"]:
        steps["discussions_thread_b_dry_run"]["non_fatal"] = True

    fractal = _run([sys.executable, str(ROOT / "scripts/run_ops_dynamical_full_ladder_chain_v1.py")])
    steps["fractal_ladder"] = fractal
    steps["fractal_ladder"]["non_fatal"] = True

    gtm_snapshot: dict[str, Any] = {}
    x_status = ""
    if GTM.is_file():
        gtm_snapshot = json.loads(GTM.read_text(encoding="utf-8-sig"))
        x_status = str((gtm_snapshot.get("channels") or {}).get("x", {}).get("status", ""))

    commander_actions = [
        "GTM FREEZE active while external_repro=0 — poll-only; no maintainer bumps",
        "Monitor Discussions #2 for external repro (re-run poll weekly)",
        "Thread B blocked until external_repro≥1 — dry-run ready: post_universal_root_discussions_thread_b_v1.py",
    ]
    if "posted_1_4" not in x_status:
        commander_actions.insert(
            0,
            "X posts 2-4: API — powershell -File scripts\\Invoke-UniversalRootXPostsApi_v1.ps1 -Post all -AcknowledgeSend (or semi-auto fallback)",
        )

    doc = {
        "schema": "universal_root_community_gtm_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "send_gate": "HOLD",
        "steps": steps,
        "gtm_channels": (gtm_snapshot.get("channels") if gtm_snapshot else {}),
        "next_commander_actions": commander_actions,
        "ok": ok,
        "reproduce": "py scripts/run_universal_root_community_gtm_chain_v1.py",
    }

    if gtm_snapshot:
        gtm_snapshot["fractal_ladder"] = {
            "status": "complete" if fractal.get("ok") else "partial",
            "artifact": "reports/ops_dynamical_full_ladder_chain_v1_latest.json",
        }
        gtm_snapshot["gtm_auto_chain"] = {
            "artifact": "reports/universal_root_community_gtm_chain_v1_latest.json",
            "last_run_utc": doc["generated_at_utc"],
        }
        gtm_snapshot["updated_at_utc"] = doc["generated_at_utc"]
        next_actions = [
            "GTM FREEZE: Phase-1A 500-pair baseline table on README before new hero GTM",
            "Collect external repro on Discussions #2 → UR-W1 unfreeze",
            "Commander: optional Thread B after external repro ≥1",
        ]
        if "posted_1_4" not in x_status:
            next_actions.insert(1, "Commander: X posts 2-4 (post_x_api_v1.py --acknowledge-send or semi-auto fallback)")
        gtm_snapshot["next_actions"] = next_actions
        GTM.write_text(json.dumps(gtm_snapshot, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "out": str(OUT), "steps_ok": {k: v.get("ok") for k, v in steps.items()}}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
