#!/usr/bin/env python3
"""Week-2/3 chain: System2 gate + promotion + Vertex staging + gated apply hooks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CHAIN_OUT = ROOT / "reports" / "mkm_system2_self_correction_gate_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_gate_argv(args: argparse.Namespace) -> list[str]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "mkm_system2_self_correction_gate_mvp_v1.py"),
        "run",
        "--max-retries",
        str(args.max_retries),
        "--export-promotion",
        "--vertex-staging",
        "--append-passed-log",
    ]
    if args.draft_file:
        cmd.extend(["--draft-file", args.draft_file])
    else:
        cmd.extend(["--draft-text", args.draft_text])
    if args.field_context_json:
        cmd.extend(["--field-context-json", args.field_context_json])
    if args.meta_layer_json:
        cmd.extend(["--meta-layer-json", args.meta_layer_json])
    if args.append_meta_layer_log:
        cmd.append("--append-meta-layer-log")
    if args.live:
        cmd.append("--live")
    if args.gemini_repair:
        cmd.append("--gemini-repair")
    if args.ollama_repair:
        cmd.append("--ollama-repair")
    if args.write_checkpoint:
        cmd.append("--write-checkpoint")
    if args.checkpoint_apply:
        cmd.append("--checkpoint-apply")
    if args.human_signoff_json:
        cmd.extend(["--human-signoff-json", args.human_signoff_json])
    if args.out_json:
        cmd.extend(["--out-json", args.out_json])
    return cmd


def _maybe_vertex_upload(args: argparse.Namespace) -> dict[str, Any] | None:
    if not args.vertex_upload:
        return None
    if not args.human_signoff_json:
        return {"ok": False, "error": "vertex_upload_requires_human_signoff_json"}
    cmd = [
        sys.executable,
        str(ROOT / "scripts/invoke_system2_vertex_staging_upload_v1.py"),
        "--human-signoff-json",
        args.human_signoff_json,
    ]
    if args.vertex_apply_upload:
        cmd.append("--apply-upload")
    if args.agent_search_corpus_dry_run:
        cmd.append("--agent-search-corpus-dry-run")
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (cp.stdout or cp.stderr or "")[-300:]
    return {"cmd": cmd, "exit_code": cp.returncode, "ok": cp.returncode == 0, "tail": tail}


def run_chain(args: argparse.Namespace) -> dict[str, Any]:
    cmd = _run_gate_argv(args)
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8", errors="replace")
    gate_ok = cp.returncode == 0
    gate_tail: Any = {}
    try:
        gate_tail = json.loads((cp.stdout or "").strip().splitlines()[-1])
    except (json.JSONDecodeError, IndexError):
        gate_tail = {"raw_stdout": (cp.stdout or "")[-200:]}

    vertex_step = _maybe_vertex_upload(args) if gate_ok else None
    chain_ok = gate_ok and (vertex_step is None or vertex_step.get("ok") is True)

    return {
        "schema": "mkm_system2_self_correction_gate_chain_v1",
        "generated_at_utc": _utc(),
        "ok": chain_ok,
        "research_only": True,
        "human_sign_off_required": True,
        "boundary_ack": "Gate chain; Vertex/checkpoint apply require human sign-off JSON.",
        "gate": {"cmd": cmd, "exit_code": cp.returncode, "ok": gate_ok, "summary": gate_tail},
        "vertex_upload": vertex_step,
        "artifacts": {
            "gate_report": args.out_json or str(ROOT / "reports/mkm_system2_self_correction_gate_mvp_v1_latest.json"),
            "promotion_candidate": str(ROOT / "reports/mkm_system2_memory_promotion_candidate_v1_latest.json"),
            "vertex_staging_jsonl": str(ROOT / "reports/mkm_system2_vertex_staging_v1.jsonl"),
            "passed_log_jsonl": str(ROOT / "reports/mkm_system2_self_correction_gate_passed_v1.jsonl"),
            "vertex_upload_report": str(ROOT / "reports/mkm_system2_vertex_staging_upload_v1_latest.json"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--draft-file")
    ap.add_argument("--draft-text")
    ap.add_argument("--field-context-json")
    ap.add_argument("--meta-layer-json")
    ap.add_argument("--append-meta-layer-log", action="store_true")
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--gemini-repair", action="store_true")
    ap.add_argument("--ollama-repair", action="store_true")
    ap.add_argument("--write-checkpoint", action="store_true")
    ap.add_argument("--checkpoint-apply", action="store_true")
    ap.add_argument("--human-signoff-json")
    ap.add_argument("--vertex-upload", action="store_true", help="Run export/upload plan after gate pass")
    ap.add_argument("--vertex-apply-upload", action="store_true", help="Actually upload MD pack to GCS")
    ap.add_argument("--agent-search-corpus-dry-run", action="store_true", help="Plan system2-gate Agent Search corpus after vertex export")
    ap.add_argument("--out-json", default=str(ROOT / "reports/mkm_system2_self_correction_gate_mvp_v1_latest.json"))
    ap.add_argument("--chain-out-json", default=str(DEFAULT_CHAIN_OUT))
    ap.add_argument("--skip-pytest", action="store_true")
    args = ap.parse_args(argv)

    if not args.draft_file and not args.draft_text:
        print("run_mkm_system2_self_correction_gate_chain_v1: --draft-file or --draft-text required", file=sys.stderr)
        return 2
    if args.checkpoint_apply and not args.human_signoff_json:
        print("run_mkm_system2_self_correction_gate_chain_v1: --checkpoint-apply requires --human-signoff-json", file=sys.stderr)
        return 2
    if args.vertex_upload and not args.human_signoff_json:
        print("run_mkm_system2_self_correction_gate_chain_v1: --vertex-upload requires --human-signoff-json", file=sys.stderr)
        return 2

    doc = run_chain(args)
    out = Path(args.chain_out_json)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if not args.skip_pytest:
        cp = subprocess.run(
            [sys.executable, "-m", "pytest", "tests/test_mkm_system2_self_correction_gate_mvp_v1.py", "-q"],
            cwd=str(ROOT),
        )
        if cp.returncode != 0:
            return cp.returncode

    print(json.dumps({"ok": doc["ok"], "chain_out_json": str(out)}))
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
