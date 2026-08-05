#!/usr/bin/env python3
"""Session end chain: resolve deep fetch → turn_meta append → CENTRAL checkpoint."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from companion_local_store_lib_v1 import env_truthy  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RESOLVE = ROOT / "scripts/resolve_deep_fetch_from_handoff_v1.py"
APPEND = ROOT / "scripts/append_mkm_cursor_turn_meta_v1.py"
CHECKPOINT = ROOT / "scripts/athena_checkpoint.py"
MISTAKE_APPEND = ROOT / "scripts/append_mkm_agent_mistake_v1.py"
PROMPT_ALIGNMENT_CHECK = ROOT / "scripts/check_commander_prompt_alignment_self_audit_v1.py"
RECEIPT_APPEND = ROOT / "scripts/append_mkm_tool_receipt_v1.py"
COMPANION_MEANING_DRYRUN = ROOT / "scripts/run_companion_meaning_pack_session_end_dryrun_v1.py"
COMPANION_APPLY_LOCAL = ROOT / "scripts/run_companion_memory_transplant_apply_local_v1.py"


def _run(cmd: list[str], *, label: str) -> int:
    proc = subprocess.run(cmd, cwd=ROOT, check=False)
    if proc.returncode != 0:
        print(f"FAIL: {label} exit {proc.returncode}", file=sys.stderr)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lane", default="infra")
    parser.add_argument("--continuity-id", required=True)
    parser.add_argument("message", nargs="?", default="")
    parser.add_argument("--message", dest="message_flag", default="", help="Alias for message arg")
    parser.add_argument("--skip-resolve", action="store_true")
    parser.add_argument("--skip-append", action="store_true")
    parser.add_argument("--skip-checkpoint", action="store_true")
    parser.add_argument("--no-patch-envelope", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--mistake", default="", help="Human-recorded mistake summary")
    parser.add_argument("--remediation", default="", help="Preventive rule for mistake registry")
    parser.add_argument("--root-cause", default="")
    parser.add_argument(
        "--self-audit-prompt",
        action="store_true",
        help="Print commander prompt alignment checklist (30s self-audit)",
    )
    parser.add_argument(
        "--alignment-fail-id",
        default="",
        help="Comma-separated check ids that failed (e.g. ai_fill_forbidden,lane_tag)",
    )
    parser.add_argument(
        "--emit-tool-receipt",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="P12 always-on: append session_end tool receipt after successful chain (default on; --no-emit-tool-receipt to skip)",
    )
    parser.add_argument(
        "--origin",
        default="agent_summary",
        choices=["commander", "agent_summary", "tool", "external_paste"],
        help="Checkpoint provenance origin (session_end default=agent_summary).",
    )
    parser.add_argument(
        "--trust",
        default="",
        choices=["", "high", "medium", "low", "unknown"],
        help="Optional trust override for checkpoint provenance.",
    )
    parser.add_argument(
        "--allow-act",
        dest="allow_act",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Pass through to athena_checkpoint provenance (external_paste always false).",
    )
    parser.add_argument(
        "--companion-meaning-pack-dryrun",
        action="store_true",
        help=(
            "Opt-in: after chain, write companion meaning-pack dry-run artifact only "
            "(applied=false · no Cursor LTM / .cursor/rules write)."
        ),
    )
    parser.add_argument(
        "--atoms-json",
        default="",
        help="Optional atoms JSON for --companion-meaning-pack-dryrun (passed through).",
    )
    parser.add_argument(
        "--companion-meaning-pack-apply-local",
        action="store_true",
        help=(
            "Opt-in: after chain, apply companion atoms to local user store only "
            "(memory/companion_local_store_v1 · applied=true for local store only · "
            "no Cursor LTM / agent LTM / PetCompanion phone). "
            "Also enabled when env MKM_COMPANION_APPLY_ON_SESSION_END=1 (default OFF)."
        ),
    )
    args = parser.parse_args(argv)

    msg = (args.message or args.message_flag or "").strip()
    if not msg:
        print("error: message required", file=sys.stderr)
        return 1

    continuity_id = args.continuity_id.strip()
    lane = args.lane.strip() or "infra"
    apply_on_end = args.companion_meaning_pack_apply_local or env_truthy(
        "MKM_COMPANION_APPLY_ON_SESSION_END"
    )

    if args.dry_run:
        print(
            f"DRY: resolve lane={lane} patch={not args.no_patch_envelope} "
            f"append continuity={continuity_id} checkpoint msg={msg!r} "
            f"mistake={args.mistake!r} self_audit_prompt={args.self_audit_prompt} "
            f"alignment_fail_id={args.alignment_fail_id!r} "
            f"emit_tool_receipt={args.emit_tool_receipt} "
            f"companion_meaning_pack_dryrun={args.companion_meaning_pack_dryrun} "
            f"companion_meaning_pack_apply_local={apply_on_end}"
        )
        return 0

    if args.self_audit_prompt:
        code = _run(
            [
                sys.executable,
                str(PROMPT_ALIGNMENT_CHECK),
                "--print-checklist",
                "--lane",
                lane,
            ],
            label="prompt_alignment_checklist",
        )
        if code != 0:
            return code
        fail_ids = [x.strip() for x in args.alignment_fail_id.split(",") if x.strip()]
        if fail_ids:
            print(f"alignment_fail_ids={fail_ids}", file=sys.stderr)

    if args.mistake.strip() and args.remediation.strip():
        code = _run(
            [
                sys.executable,
                str(MISTAKE_APPEND),
                "--lane",
                lane,
                "--source",
                "human",
                "--mistake",
                args.mistake.strip(),
                "--remediation",
                args.remediation.strip(),
                "--root-cause",
                (args.root_cause or "").strip(),
                "--continuity-id",
                continuity_id,
            ],
            label="append_mistake",
        )
        if code != 0:
            return code

    if not args.skip_resolve:
        resolve_cmd = [
            sys.executable,
            str(RESOLVE),
            "--lane",
            lane,
        ]
        if not args.no_patch_envelope:
            resolve_cmd.append("--patch-envelope")
        code = _run(resolve_cmd, label="resolve_deep_fetch")
        if code != 0:
            return code

    if not args.skip_append:
        code = _run(
            [
                sys.executable,
                str(APPEND),
                "--lane",
                lane,
                "--continuity-id",
                continuity_id,
                "--checkpoint-message",
                msg,
            ],
            label="append_turn_meta",
        )
        if code != 0:
            return code

    if not args.skip_checkpoint:
        ck_cmd = [
            sys.executable,
            str(CHECKPOINT),
            "--continuity-id",
            continuity_id,
            "--lane",
            lane,
            "--skip-turn-meta",
            "--origin",
            args.origin,
        ]
        if args.trust:
            ck_cmd.extend(["--trust", args.trust])
        if args.allow_act is True:
            ck_cmd.append("--allow-act")
        elif args.allow_act is False:
            ck_cmd.append("--no-allow-act")
        ck_cmd.append(msg)
        code = _run(ck_cmd, label="athena_checkpoint")
        if code != 0:
            return code

    if args.emit_tool_receipt:
        code = _run(
            [
                sys.executable,
                str(RECEIPT_APPEND),
                "--lane",
                lane,
                "--continuity-id",
                continuity_id,
                "--cmd-summary",
                f"run_mkm_cursor_session_end_v1 lane={lane}",
                "--exit-code",
                "0",
                "--source",
                "session_end",
                "--artifact",
                "reports/mkm_tool_receipts_v1.jsonl",
                "--notes",
                msg[:400],
            ],
            label="append_tool_receipt",
        )
        if code != 0:
            return code

    if args.companion_meaning_pack_dryrun:
        dry_cmd = [
            sys.executable,
            str(COMPANION_MEANING_DRYRUN),
            "--lane",
            lane,
            "--continuity-id",
            continuity_id,
            "--message",
            msg,
        ]
        atoms = (args.atoms_json or "").strip()
        if atoms:
            dry_cmd.extend(["--atoms-json", atoms])
        code = _run(dry_cmd, label="companion_meaning_pack_dryrun")
        if code != 0:
            return code

    if apply_on_end:
        apply_cmd = [
            sys.executable,
            str(COMPANION_APPLY_LOCAL),
            "--lane",
            lane,
            "--continuity-id",
            continuity_id,
            "--message",
            msg,
            "--commander-phrase",
            "실제 이식 진행해",
        ]
        code = _run(apply_cmd, label="companion_meaning_pack_apply_local")
        if code != 0:
            return code

    print(f"OK: session_end lane={lane} continuity_id={continuity_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
