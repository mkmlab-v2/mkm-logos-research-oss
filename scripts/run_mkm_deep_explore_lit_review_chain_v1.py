#!/usr/bin/env python3
"""P1/P2 chain: explore → LIT_REVIEW → citation_lock [→ router_index → fact_support]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
EXPLORE = ROOT / "scripts" / "mkm_deep_explore_v1.py"
BUILD = ROOT / "scripts" / "build_mkm_deep_explore_lit_review_v1.py"
CITATION_LOCK = ROOT / "scripts" / "check_research_lit_review_citation_lock_v1.py"
ROUTER_INDEX = ROOT / "scripts" / "build_mkm_deep_research_router_index_v1.py"
FACT_SUPPORT = ROOT / "scripts" / "check_research_lit_review_fact_support_v1.py"
DEFAULT_OUT = ROOT / "reports" / "mkm_deep_explore_lit_review_chain_v1_latest.json"


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
    parser = argparse.ArgumentParser(description="MKM deep explore → LIT_REVIEW → citation_lock chain")
    parser.add_argument("--query", required=True)
    parser.add_argument("--max-per-lane", type=int, default=8)
    parser.add_argument("--timeout-sec", type=float, default=25.0)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--skip-explore", action="store_true", help="Use existing JSONL from latest explore manifest")
    parser.add_argument("--jsonl", type=Path, default=None, help="Explicit explore JSONL (implies --skip-explore)")
    parser.add_argument("--min-pass-rate", type=float, default=0.85)
    parser.add_argument("--include-p2", action="store_true", help="Add router index + FACT Phase B support judge")
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    steps: dict[str, Any] = {}
    jsonl_path: Path | None = args.jsonl.resolve() if args.jsonl else None

    if not args.skip_explore and jsonl_path is None:
        _log("chain P1: step 1/3 explore")
        explore_cmd = [
            sys.executable,
            str(EXPLORE),
            "--query",
            args.query,
            "--max-per-lane",
            str(args.max_per_lane),
            "--timeout-sec",
            str(args.timeout_sec),
        ]
        if args.offline:
            explore_cmd.append("--offline")
        proc = _run(explore_cmd)
        steps["explore"] = {"exit_code": proc.returncode, "stdout": proc.stdout.strip(), "stderr": proc.stderr.strip()}
        if proc.returncode != 0:
            doc = {"ok": False, "step": "explore", "steps": steps}
            print(json.dumps(doc, ensure_ascii=False))
            return proc.returncode
        explore_doc = json.loads(proc.stdout.strip())
        jsonl_rel = explore_doc.get("raw_jsonl")
        if not jsonl_rel:
            print(json.dumps({"ok": False, "error": "explore missing raw_jsonl"}, ensure_ascii=False))
            return 1
        jsonl_path = (ROOT / str(jsonl_rel)).resolve()
    elif jsonl_path is None:
        manifest_path = ROOT / "reports" / "mkm_deep_explore_v1_latest.json"
        if not manifest_path.is_file():
            print(json.dumps({"ok": False, "error": "missing explore manifest; run explore first"}, ensure_ascii=False))
            return 2
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        jsonl_path = (ROOT / str(manifest["raw_jsonl"])).resolve()

    if not jsonl_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing jsonl: {jsonl_path}"}, ensure_ascii=False))
        return 2

    _log("chain P1: step 2/3 build LIT_REVIEW")
    build_proc = _run(
        [
            sys.executable,
            str(BUILD),
            "--jsonl",
            str(jsonl_path),
            "--query",
            args.query,
        ]
    )
    steps["build_lit_review"] = {
        "exit_code": build_proc.returncode,
        "stdout": build_proc.stdout.strip(),
        "stderr": build_proc.stderr.strip(),
    }
    if build_proc.returncode != 0:
        print(json.dumps({"ok": False, "step": "build_lit_review", "steps": steps}, ensure_ascii=False))
        return build_proc.returncode
    build_doc = json.loads(build_proc.stdout.strip())
    lit_path = ROOT / str(build_doc["out_path"])

    _log("chain P1: step 3/3 citation_lock")
    lock_cmd = [
        sys.executable,
        str(CITATION_LOCK),
        "--input",
        str(lit_path),
        "--min-pass-rate",
        str(args.min_pass_rate),
    ]
    if args.offline:
        lock_cmd.append("--offline")
    else:
        lock_cmd.extend(["--min-total-ids", "1"])
    lock_proc = _run(lock_cmd)
    steps["citation_lock"] = {
        "exit_code": lock_proc.returncode,
        "stdout": lock_proc.stdout.strip(),
        "stderr": lock_proc.stderr.strip(),
    }
    if lock_proc.returncode != 0:
        print(json.dumps({"ok": False, "step": "citation_lock", "steps": steps}, ensure_ascii=False))
        return lock_proc.returncode
    lock_doc = json.loads(lock_proc.stdout.strip())

    router_doc: dict[str, Any] | None = None
    fact_doc: dict[str, Any] | None = None
    if args.include_p2:
        _log("chain P2: step 4/5 router_index")
        router_proc = _run(
            [
                sys.executable,
                str(ROUTER_INDEX),
                "--jsonl",
                str(jsonl_path),
                "--query",
                args.query,
            ]
        )
        steps["router_index"] = {
            "exit_code": router_proc.returncode,
            "stdout": router_proc.stdout.strip(),
            "stderr": router_proc.stderr.strip(),
        }
        if router_proc.returncode != 0:
            print(json.dumps({"ok": False, "step": "router_index", "steps": steps}, ensure_ascii=False))
            return router_proc.returncode
        router_doc = json.loads(router_proc.stdout.strip())

        _log("chain P2: step 5/5 fact_support (Phase B)")
        fact_cmd = [
            sys.executable,
            str(FACT_SUPPORT),
            "--input",
            str(lit_path),
            "--jsonl",
            str(jsonl_path),
            "--min-pass-rate",
            str(args.min_pass_rate),
        ]
        if args.offline:
            fact_cmd.append("--offline")
        else:
            fact_cmd.extend(["--min-total-claims", "1"])
        fact_proc = _run(fact_cmd)
        steps["fact_support"] = {
            "exit_code": fact_proc.returncode,
            "stdout": fact_proc.stdout.strip(),
            "stderr": fact_proc.stderr.strip(),
        }
        if fact_proc.returncode != 0:
            print(json.dumps({"ok": False, "step": "fact_support", "steps": steps}, ensure_ascii=False))
            return fact_proc.returncode
        fact_doc = json.loads(fact_proc.stdout.strip())

    doc = {
        "schema": "mkm_deep_explore_lit_review_chain_v1",
        "chain_version": "1.1.0" if args.include_p2 else "1.0.0",
        "generated_at_utc": _utc_now(),
        "ok": True,
        "query": args.query,
        "raw_jsonl": _posix_path(jsonl_path),
        "lit_review_md": _posix_path(lit_path),
        "citation_lock": lock_doc,
        "router_index": router_doc,
        "fact_support": fact_doc,
        "research_only": True,
        "send_gate": "HOLD",
        "reproduce": f'py scripts/run_mkm_deep_explore_lit_review_chain_v1.py --query "{args.query}"'
        + (" --include-p2" if args.include_p2 else ""),
        "steps": steps,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out_json": _posix_path(args.out_json), "lit_review_md": doc["lit_review_md"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
