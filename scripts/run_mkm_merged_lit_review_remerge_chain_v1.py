#!/usr/bin/env python3
"""P1-D: raw drop detect → incremental MERGED patch → full citation/fact gate chain."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MERGED = ROOT / "docs" / "research" / "NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md"
DEFAULT_RAW_DIR = ROOT / "docs" / "research" / "raw"
DEFAULT_TOPIC_SLUG = "next_gen_hybrid_ai_mkm"
DEFAULT_QUERY = "next gen hybrid AI memory edge cloud routing"
DEFAULT_OUT = ROOT / "reports" / "mkm_merged_lit_review_remerge_chain_v1_latest.json"
DEFAULT_BENCH_TASKS = ROOT / "tests" / "fixtures" / "mkm_deep_research_bench_tasks_v1.json"
INCREMENTAL = ROOT / "scripts" / "build_mkm_merged_lit_review_incremental_v1.py"
GATE_CHAIN = ROOT / "scripts" / "run_mkm_merged_lit_review_gate_chain_v1.py"
SHALLOW_TRIGGER = ROOT / "scripts" / "build_mkm_raw_drop_shallow_trigger_v1.py"
DR_BENCH = ROOT / "scripts" / "run_mkm_deep_research_bench_mini_v1.py"


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
    parser = argparse.ArgumentParser(description="Raw drop incremental re-merge + full gate chain (P1-D)")
    parser.add_argument("--merged", type=Path, default=DEFAULT_MERGED)
    parser.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    parser.add_argument("--topic-slug", default=DEFAULT_TOPIC_SLUG)
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--offline", action="store_true")
    parser.add_argument("--use-ollama", action="store_true")
    parser.add_argument("--no-ollama", action="store_true")
    parser.add_argument("--force-all", action="store_true")
    parser.add_argument("--manifest", type=Path, default=None)
    parser.add_argument("--skip-gate", action="store_true")
    parser.add_argument("--force-gate", action="store_true", help="Run gate even when manifest bootstrap only")
    parser.add_argument("--force-shallow-trigger", action="store_true")
    parser.add_argument("--skip-shallow-trigger", action="store_true")
    parser.add_argument("--skip-handoff", action="store_true")
    parser.add_argument("--include-bench", action="store_true", help="Run DR bench mini after merge/gate when triggered")
    parser.add_argument("--force-bench", action="store_true", help="Run DR bench even on noop remerge")
    parser.add_argument("--skip-bench", action="store_true")
    parser.add_argument("--bench-tasks", type=Path, default=DEFAULT_BENCH_TASKS)
    parser.add_argument("--bench-out-json", type=Path, default=ROOT / "reports" / "mkm_deep_research_bench_mini_remerge_hook_latest.json")
    parser.add_argument("--min-pass-rate", type=float, default=0.85)
    parser.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()

    merged_path = args.merged.resolve()
    if not merged_path.is_file():
        print(json.dumps({"ok": False, "error": f"missing merged: {merged_path}"}, ensure_ascii=False))
        return 2

    steps: dict[str, Any] = {}
    total_steps = 4

    _log(f"remerge chain: step 1/{total_steps} incremental patch")
    inc_cmd = [
        sys.executable,
        str(INCREMENTAL),
        "--merged",
        str(merged_path),
        "--raw-dir",
        str(args.raw_dir.resolve()),
        "--topic-slug",
        args.topic_slug,
        "--query",
        args.query,
    ]
    if args.offline:
        inc_cmd.append("--offline")
    if args.use_ollama:
        inc_cmd.append("--use-ollama")
    if args.no_ollama:
        inc_cmd.append("--no-ollama")
    if args.force_all:
        inc_cmd.append("--force-all")
    if args.manifest:
        inc_cmd.extend(["--manifest", str(args.manifest.resolve())])
    inc_proc = _run(inc_cmd)
    steps["incremental_patch"] = {
        "exit_code": inc_proc.returncode,
        "stdout": inc_proc.stdout.strip(),
        "stderr": inc_proc.stderr.strip(),
    }
    if inc_proc.returncode != 0:
        print(json.dumps({"ok": False, "step": "incremental_patch", "steps": steps}, ensure_ascii=False))
        return inc_proc.returncode
    incremental_doc = json.loads(inc_proc.stdout.strip())

    shallow_doc: dict[str, Any] | None = None
    run_shallow = (
        not args.skip_shallow_trigger
        and (incremental_doc.get("changed") or args.force_shallow_trigger)
        and (incremental_doc.get("changed_raw_paths") or args.force_shallow_trigger)
    )
    if run_shallow:
        _log(f"remerge chain: step 2/{total_steps} shallow router trigger (Phase B)")
        trigger_cmd = [
            sys.executable,
            str(SHALLOW_TRIGGER),
            "--merged",
            str(merged_path),
            "--topic-slug",
            args.topic_slug,
            "--query",
            args.query,
        ]
        if args.use_ollama:
            trigger_cmd.append("--use-ollama")
        if args.no_ollama:
            trigger_cmd.append("--no-ollama")
        if args.skip_handoff:
            trigger_cmd.append("--skip-handoff")
        plane_hint = incremental_doc.get("plane_hint")
        if isinstance(plane_hint, str) and plane_hint:
            trigger_cmd.extend(["--plane-hint", plane_hint])
        for raw_path in incremental_doc.get("changed_raw_paths") or []:
            trigger_cmd.extend(["--raw-path", str(ROOT / raw_path)])
        if args.force_shallow_trigger and not incremental_doc.get("changed_raw_paths"):
            for raw_md in sorted(args.raw_dir.resolve().glob("*.md")):
                if "_explore_" not in raw_md.name.lower():
                    trigger_cmd.extend(["--raw-path", str(raw_md.resolve())])
        trigger_proc = _run(trigger_cmd)
        steps["shallow_trigger"] = {
            "exit_code": trigger_proc.returncode,
            "stdout": trigger_proc.stdout.strip(),
            "stderr": trigger_proc.stderr.strip(),
        }
        if trigger_proc.returncode != 0:
            print(json.dumps({"ok": False, "step": "shallow_trigger", "steps": steps}, ensure_ascii=False))
            return trigger_proc.returncode
        shallow_doc = json.loads(trigger_proc.stdout.strip())

    skip_gate = args.skip_gate or (
        not incremental_doc.get("changed") and not args.force_gate and not run_shallow
    )

    gate_doc: dict[str, Any] | None = None
    if not skip_gate:
        _log(f"remerge chain: step 3/{total_steps} full gate chain (citation + fact + router + handoff)")
        gate_out = args.out_json.parent / "mkm_merged_lit_review_gate_chain_remerge_tmp.json"
        gate_cmd = [
            sys.executable,
            str(GATE_CHAIN),
            "--input",
            str(merged_path),
            "--query",
            args.query,
            "--min-pass-rate",
            str(args.min_pass_rate),
            "--out-json",
            str(gate_out),
        ]
        if args.offline:
            gate_cmd.append("--offline")
        if args.skip_handoff:
            gate_cmd.append("--skip-handoff")
        gate_proc = _run(gate_cmd)
        steps["gate_chain"] = {
            "exit_code": gate_proc.returncode,
            "stdout": gate_proc.stdout.strip(),
            "stderr": gate_proc.stderr.strip(),
        }
        if gate_proc.returncode != 0:
            print(json.dumps({"ok": False, "step": "gate_chain", "steps": steps}, ensure_ascii=False))
            return gate_proc.returncode
        if gate_out.is_file():
            gate_doc = json.loads(gate_out.read_text(encoding="utf-8"))

    bench_doc: dict[str, Any] | None = None
    run_bench = not args.skip_bench and (
        args.force_bench
        or incremental_doc.get("changed")
        or (args.include_bench and (gate_doc or {}).get("ok"))
    )
    if run_bench:
        _log(f"remerge chain: step 4/{total_steps} DR bench mini hook (P2-G)")
        bench_cmd = [
            sys.executable,
            str(DR_BENCH),
            "--tasks",
            str(args.bench_tasks.resolve()),
            "--include-router",
            "--out-json",
            str(args.bench_out_json.resolve()),
        ]
        if args.offline:
            bench_cmd.append("--offline")
        bench_proc = _run(bench_cmd)
        steps["dr_bench_mini"] = {
            "exit_code": bench_proc.returncode,
            "stdout": bench_proc.stdout.strip(),
            "stderr": bench_proc.stderr.strip(),
        }
        if bench_proc.returncode != 0:
            print(json.dumps({"ok": False, "step": "dr_bench_mini", "steps": steps}, ensure_ascii=False))
            return bench_proc.returncode
        if args.bench_out_json.is_file():
            bench_doc = json.loads(args.bench_out_json.read_text(encoding="utf-8"))

    chain_ok = True
    if gate_doc is not None and not gate_doc.get("ok"):
        chain_ok = False
    if bench_doc is not None and not bench_doc.get("ok"):
        chain_ok = False

    doc = {
        "schema": "mkm_merged_lit_review_remerge_chain_v1",
        "version": "1.1.0",
        "generated_at_utc": _utc_now(),
        "merged_md": _posix_path(merged_path),
        "topic_slug": args.topic_slug,
        "query": args.query,
        "merge_mode": "incremental_patch_full_gate",
        "incremental_patch": incremental_doc,
        "shallow_trigger": shallow_doc,
        "gate_chain": gate_doc,
        "gate_skipped": skip_gate,
        "dr_bench_mini": bench_doc,
        "bench_skipped": not run_bench,
        "ok": chain_ok,
        "send_gate": "HOLD",
        "research_only": True,
        "reproduce": (
            f'py scripts/run_mkm_merged_lit_review_remerge_chain_v1.py '
            f'--merged "{_posix_path(merged_path)}" --topic-slug {args.topic_slug}'
        ),
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": chain_ok,
                "out_json": _posix_path(args.out_json),
                "changed": incremental_doc.get("changed"),
                "new_arxiv_id_count": incremental_doc.get("new_arxiv_id_count", 0),
                "shallow_trigger_ok": (shallow_doc or {}).get("ok"),
                "gate_ok": (gate_doc or {}).get("ok"),
                "bench_ok": (bench_doc or {}).get("ok"),
                "bench_skipped": not run_bench,
            },
            ensure_ascii=False,
        )
    )
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
