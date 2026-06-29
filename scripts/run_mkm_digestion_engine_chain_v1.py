#!/usr/bin/env python3
"""MKM digestion engine chain: Mastication → Wiring → Fact-Lock gate (B-track)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports" / "mkm_digestion_engine_chain_v1_latest.json"
BUILD = ROOT / "scripts" / "build_mkm_research_digested_facts_v1.py"
WIRE = ROOT / "scripts" / "map_digested_facts_to_mkm_plane_v1.py"
ACTIVE_FACT = ROOT / "scripts" / "check_digested_numeric_fact_v1.py"
GATE = ROOT / "scripts" / "check_mkm_digested_facts_gate_v1.py"
CITATION_LOCK = ROOT / "scripts" / "check_research_lit_review_citation_lock_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _log(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def _posix_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _run(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="Tier 0 markdown → digested JSON → wiring → gate")
    parser.add_argument("--input", type=Path, required=True, help="Tier 0 markdown under docs/research/raw/")
    parser.add_argument("--topic-slug", default=None)
    parser.add_argument("--digested-out", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--offline", action="store_true", help="citation lock offline mode")
    parser.add_argument("--skip-citation-lock", action="store_true")
    parser.add_argument("--skip-active-fact", action="store_true")
    parser.add_argument("--skip-gate", action="store_true")
    parser.add_argument("--no-table-heuristic", action="store_true")
    parser.add_argument(
        "--production",
        action="store_true",
        help="production digestion: MKM_DIGESTION_PRODUCTION=1 for active fact-lite child",
    )
    args = parser.parse_args()

    md_path = args.input.resolve()
    if not md_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing input: {md_path}"}, ensure_ascii=False))
        return 2

    digested_out = (
        args.digested_out.resolve()
        if args.digested_out
        else ROOT / "docs/final/artifacts" / f"{md_path.stem}_digested_facts_latest.json"
    )

    steps: dict[str, Any] = {}

    total_steps = 5

    _log(f"digestion chain: step 1/{total_steps} mastication (build + schema)")
    build_cmd = [
        sys.executable,
        str(BUILD),
        "--input",
        str(md_path),
        "--out",
        str(digested_out),
        "--strict",
    ]
    if args.topic_slug:
        build_cmd.extend(["--topic-slug", args.topic_slug])
    if args.no_table_heuristic:
        build_cmd.append("--no-table-heuristic")
    build_proc = _run(build_cmd)
    steps["mastication"] = {
        "exit_code": build_proc.returncode,
        "stdout": build_proc.stdout.strip(),
    }
    if build_proc.returncode != 0:
        steps["mastication"]["stderr"] = build_proc.stderr.strip()
        _write_chain_report(args.out_json, md_path, digested_out, steps, ok=False, production_mode=args.production)
        return build_proc.returncode

    _log(f"digestion chain: step 2/{total_steps} wiring")
    wire_proc = _run(
        [
            sys.executable,
            str(WIRE),
            "--input",
            str(digested_out),
        ]
    )
    steps["wiring"] = {"exit_code": wire_proc.returncode, "stdout": wire_proc.stdout.strip()}
    if wire_proc.returncode != 0:
        steps["wiring"]["stderr"] = wire_proc.stderr.strip()
        _write_chain_report(args.out_json, md_path, digested_out, steps, ok=False, production_mode=args.production)
        return wire_proc.returncode

    if not args.skip_active_fact:
        _log(f"digestion chain: step 3/{total_steps} active fact-lite")
        active_cmd = [
            sys.executable,
            str(ACTIVE_FACT),
            "--input",
            str(digested_out),
        ]
        if args.offline:
            active_cmd.append("--offline")
        if args.production:
            active_cmd.append("--production")
        active_env = os.environ.copy()
        if args.production:
            active_env["MKM_DIGESTION_PRODUCTION"] = "1"
        active_proc = subprocess.run(
            active_cmd,
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            env=active_env,
        )
        steps["active_fact_lite"] = {
            "exit_code": active_proc.returncode,
            "stdout": active_proc.stdout.strip(),
        }
        if active_proc.returncode != 0:
            steps["active_fact_lite"]["stderr"] = active_proc.stderr.strip()
            _write_chain_report(args.out_json, md_path, digested_out, steps, ok=False, production_mode=args.production)
            return active_proc.returncode
    else:
        steps["active_fact_lite"] = {"skipped": True}

    if not args.skip_citation_lock:
        _log(f"digestion chain: step 4/{total_steps} citation lock (source md)")
        cit_cmd = [
            sys.executable,
            str(CITATION_LOCK),
            "--input",
            str(md_path),
            "--min-total-ids",
            "0",
        ]
        if args.offline:
            cit_cmd.append("--offline")
        cit_proc = _run(cit_cmd)
        steps["citation_lock"] = {
            "exit_code": cit_proc.returncode,
            "stdout": cit_proc.stdout.strip(),
        }
        if cit_proc.returncode != 0:
            steps["citation_lock"]["stderr"] = cit_proc.stderr.strip()
            _write_chain_report(args.out_json, md_path, digested_out, steps, ok=False, production_mode=args.production)
            return cit_proc.returncode
    else:
        steps["citation_lock"] = {"skipped": True}

    if not args.skip_gate:
        _log(f"digestion chain: step 5/{total_steps} fact-lock gate")
        gate_proc = _run(
            [
                sys.executable,
                str(GATE),
                "--input",
                str(digested_out),
                "--strict-schema",
            ]
        )
        steps["fact_lock_gate"] = {
            "exit_code": gate_proc.returncode,
            "stdout": gate_proc.stdout.strip(),
        }
        if gate_proc.returncode != 0:
            steps["fact_lock_gate"]["stderr"] = gate_proc.stderr.strip()
            _write_chain_report(args.out_json, md_path, digested_out, steps, ok=False, production_mode=args.production)
            return gate_proc.returncode
    else:
        steps["fact_lock_gate"] = {"skipped": True}

    _write_chain_report(args.out_json, md_path, digested_out, steps, ok=True, production_mode=args.production)
    print(
        json.dumps(
            {
                "ok": True,
                "digested_path": _posix_path(digested_out),
                "chain_report": _posix_path(args.out_json.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0


def _write_chain_report(
    out_json: Path,
    md_path: Path,
    digested_path: Path,
    steps: dict[str, Any],
    *,
    ok: bool,
    production_mode: bool = False,
) -> None:
    doc = {
        "schema": "mkm_digestion_engine_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc_now(),
        "ok": ok,
        "source_tier0_path": _posix_path(md_path),
        "digested_facts_path": _posix_path(digested_path),
        "steps": steps,
        "production_mode": production_mode,
        "research_only": True,
        "send_gate": "HOLD",
        "reproduce": f"py scripts/run_mkm_digestion_engine_chain_v1.py --input {_posix_path(md_path)}",
    }
    out_path = out_json.resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
