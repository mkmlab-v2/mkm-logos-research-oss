#!/usr/bin/env python3
"""Phase 11-O: NL research sandbox pack build + MCP register/push + bridge refresh [HYPO]."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_OUT = ROOT / "reports/logos_graphrag_phase11o_nl_sandbox_sync_chain_v1_latest.json"
PACK_MANIFEST = ROOT / "reports/notebooklm_universal_root_research_pack_v1_latest.json"
PUSH_OUT = ROOT / "reports/notebooklm_universal_root_research_pack_push_v1_latest.json"
REGISTER_OUT = ROOT / "reports/notebooklm_research_sandbox_mcp_register_latest.json"
BRIDGE_OUT = ROOT / "docs/final/artifacts/universal_root_research_impl_bridge_v1_latest.json"
GATE_CHAIN_OUT = ROOT / "reports/universal_root_lexicon_merged_lit_review_gate_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(label: str, cmd: list[str], *, optional: bool = False) -> dict:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    ok = proc.returncode == 0
    row = {
        "label": label,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "ok": ok,
        "tail": ((proc.stdout or "") + (proc.stderr or "")).strip()[-500:],
    }
    if not ok and not optional:
        raise SystemExit(f"{label} failed rc={proc.returncode}\n{row['tail']}")
    return row


def _read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-register", action="store_true")
    ap.add_argument("--skip-push", action="store_true")
    ap.add_argument(
        "--cursor-mcp-results",
        type=Path,
        default=None,
        help="Record push rows from Cursor-injected MCP (stdio push fails when chrome profile locked)",
    )
    ap.add_argument("--dry-run-push", action="store_true")
    ap.add_argument("--skip-gate-spec", action="store_true")
    ap.add_argument("--skip-evidence-pack", action="store_true")
    ap.add_argument("--force-second-mcp", action="store_true")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict] = []
    steps.append(_run("build_nl_research_pack", [PY, "scripts/build_notebooklm_universal_root_research_pack_v1.py"]))

    if not args.skip_register:
        steps.append(
            _run(
                "register_nl_research_sandbox",
                [PY, "scripts/register_notebooklm_research_sandbox_mcp_v1.py", "--no-select"],
            )
        )

    if args.cursor_mcp_results:
        steps.append(
            _run(
                "record_cursor_mcp_push",
                [
                    PY,
                    "scripts/record_notebooklm_universal_root_cursor_push_v1.py",
                    "--results-json",
                    str(args.cursor_mcp_results),
                ],
            )
        )
    if not args.skip_push:
        push_cmd = [PY, "scripts/push_notebooklm_universal_root_research_pack_nlm_v1.py"]
        if args.dry_run_push:
            push_cmd = [PY, "scripts/push_notebooklm_universal_root_full_cursor_mcp_v1.py", "--list"]
        steps.append(_run("push_nl_research_pack_nlm", push_cmd, optional=args.dry_run_push))

    if not args.skip_gate_spec:
        steps.append(_run("refresh_gate_spec_baseline", [PY, "scripts/refresh_universal_root_gate_spec_baseline_v1.py"]))
        steps.append(_run("check_gate_spec", [PY, "scripts/check_universal_root_gate_spec_v1.py"]))

    steps.append(
        _run(
            "build_research_impl_bridge",
            [
                PY,
                "scripts/build_universal_root_research_impl_bridge_v1.py",
                "--gate-chain-json",
                str(GATE_CHAIN_OUT),
                "--strict",
            ],
        )
    )

    if not args.skip_evidence_pack:
        steps.append(_run("evidence_pack", [PY, "scripts/build_logos_graphrag_bridge_evidence_pack_v1.py"], optional=True))

    register_doc = _read_json(REGISTER_OUT)
    push_doc = _read_json(PUSH_OUT)
    pack_doc = _read_json(PACK_MANIFEST)
    bridge_doc = _read_json(BRIDGE_OUT)

    if args.cursor_mcp_results:
        push_ok = bool(push_doc.get("all_ok"))
    elif args.skip_push:
        push_ok = True
    else:
        push_ok = bool(push_doc.get("all_ok"))
    if args.dry_run_push:
        push_ok = True

    all_ok = (
        all(s.get("ok") for s in steps)
        and bool(bridge_doc.get("bridge_ok"))
        and bool(pack_doc.get("file_count"))
        and push_ok
        and (register_doc.get("success") is not False if not args.skip_register else True)
    )

    report = {
        "schema": "logos_graphrag_phase11o_nl_sandbox_sync_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "hypothesis_class": "HYPO",
        "research_only": True,
        "send_gate": "HOLD",
        "all_ok": all_ok,
        "notebook_mcp_id": "14-universal-lexicon-dr",
        "pack_file_count": pack_doc.get("file_count"),
        "nl_register_success": register_doc.get("success"),
        "nl_push_all_ok": push_doc.get("all_ok"),
        "nl_push_ok_count": push_doc.get("ok_count"),
        "nl_push_method": push_doc.get("method"),
        "bridge_ok": bridge_doc.get("bridge_ok"),
        "gate_spec_phase": (bridge_doc.get("implementation_snapshot") or {}).get("gate_spec_phase"),
        "pack_manifest": str(PACK_MANIFEST.relative_to(ROOT)).replace("\\", "/"),
        "push_artifact": str(PUSH_OUT.relative_to(ROOT)).replace("\\", "/"),
        "steps": steps,
        "reproduce": "py scripts/run_logos_graphrag_phase11o_nl_sandbox_sync_chain_v1.py",
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": all_ok,
                "out": str(args.out),
                "pack_file_count": pack_doc.get("file_count"),
                "nl_push_ok_count": push_doc.get("ok_count"),
                "gate_spec_phase": report["gate_spec_phase"],
            },
            ensure_ascii=False,
        )
    )
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
