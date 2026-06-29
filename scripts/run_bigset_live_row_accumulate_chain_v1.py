#!/usr/bin/env python3
"""Memory-light live accumulate: BigSet rows=1 → merge dedup → ingest gates (--skip-bridge).

Remote LLM (OpenRouter/Azure); local RAM stays low vs Ollama large-ctx.

Reproducible:
  py scripts/run_bigset_live_row_accumulate_chain_v1.py --dry-run-batch tests/fixtures/bigset/sample_theology_tier0_rows_v1.csv
  py scripts/run_bigset_live_row_accumulate_chain_v1.py --live --free-tier
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PY = sys.executable
INGEST_CHAIN = ROOT / "scripts/run_bigset_ingest_spike_chain_v1.py"
MERGE_SCRIPT = ROOT / "scripts/merge_bigset_tier0_csv_accumulate_v1.py"
OUT_REPORT = ROOT / "reports/bigset_live_row_accumulate_chain_v1_latest.json"
OUT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_live_row_accumulate_chain_v1_latest.json"
DEFAULT_BATCH = ROOT / "docs/final/artifacts/bigset_tier0_live_batch_v1_latest.csv"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, env: dict[str, str] | None = None) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, env=env)
    tail = (proc.stdout or proc.stderr or "").strip()[-400:]
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": tail,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--topic-slug", default="benei_haelohim_cross_refs")
    ap.add_argument("--live", action="store_true", help="invoke bigset CLI rows=1 (BYOK)")
    ap.add_argument(
        "--dry-run-batch",
        type=Path,
        help="CI/offline: copy fixture as batch instead of live bigset",
    )
    ap.add_argument("--rows", type=int, default=1, help="live rows per invocation (default 1)")
    ap.add_argument("--timeout-sec", type=int, default=900)
    ap.add_argument("--free-tier", action="store_true")
    ap.add_argument("--free-tier-mode", choices=["openrouter_free", "ollama", "azure"], default=None)
    ap.add_argument("--skip-ingest", action="store_true")
    ap.add_argument("--batch-csv", type=Path, default=DEFAULT_BATCH)
    ap.add_argument(
        "--prompt",
        default=None,
        help="override live BigSet prompt (default: THEOLOGY_PROMPT_TEMPLATE)",
    )
    ap.add_argument(
        "--prompt-preset",
        choices=["theology", "nephilim"],
        default=None,
        help="preset prompt (nephilim → NEPHILIM_WATCHER_PROMPT_TEMPLATE)",
    )
    args = ap.parse_args()

    if args.live and args.dry_run_batch:
        print(json.dumps({"ok": False, "error": "live_and_dry_run_batch_mutually_exclusive"}), file=sys.stderr)
        return 2

    slug = args.topic_slug.strip().replace(" ", "_")
    target_csv = ROOT / "docs/research/raw" / f"bigset_{slug}_tier0_v1.csv"
    md_out = ROOT / "docs/research/raw" / f"bigset_{slug}_tier0_v1.md"
    batch_csv = args.batch_csv if args.batch_csv.is_absolute() else (ROOT / args.batch_csv)

    nodes: list[dict[str, Any]] = []
    ok_all = True
    child_env = None
    free_profile: dict[str, Any] | None = None

    if args.free_tier:
        from scripts.bigset_free_tier_profile_v1 import (
            apply_profile_to_environ,
            profile_public_snapshot,
            resolve_profile,
        )

        mode = "ollama_local" if args.free_tier_mode == "ollama" else args.free_tier_mode
        if args.free_tier_mode == "azure":
            mode = "azure_openai"
        prof = resolve_profile(mode=mode)
        apply_profile_to_environ(prof)
        free_profile = profile_public_snapshot(prof)
        child_env = os.environ.copy()
        nodes.append({"step": "free_tier_profile", "ok": True, "profile": free_profile})

    if args.dry_run_batch:
        src = args.dry_run_batch if args.dry_run_batch.is_absolute() else (ROOT / args.dry_run_batch)
        if not src.is_file():
            print(json.dumps({"ok": False, "error": f"missing dry-run batch: {src}"}), file=sys.stderr)
            return 2
        batch_csv.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, batch_csv)
        nodes.append(
            {
                "step": "dry_run_batch",
                "ok": True,
                "batch_csv": str(batch_csv),
                "source": str(src),
            }
        )
    elif args.live:
        from scripts.bigset_agent_bridge_v1 import (
            NEPHILIM_WATCHER_PROMPT_TEMPLATE,
            THEOLOGY_PROMPT_TEMPLATE,
            _read_csv_rows,
            _resolve_prompt,
            _run_live_bigset,
        )

        batch_csv.parent.mkdir(parents=True, exist_ok=True)
        if batch_csv.is_file():
            batch_csv.unlink()
        if args.prompt:
            prompt_base = str(args.prompt)
        elif getattr(args, "prompt_preset", None) == "nephilim":
            prompt_base = NEPHILIM_WATCHER_PROMPT_TEMPLATE
        else:
            prompt_base = THEOLOGY_PROMPT_TEMPLATE
        live = _run_live_bigset(
            prompt=_resolve_prompt(prompt_base, live=True),
            rows=max(1, int(args.rows)),
            out_csv=batch_csv,
            timeout_sec=max(60, int(args.timeout_sec)),
        )
        live_ok = bool(live.get("ok") or live.get("partial_csv"))
        if live_ok and batch_csv.is_file():
            live_ok = len(_read_csv_rows(batch_csv)) >= 1
        nodes.append({**live, "step": "live_bigset_batch", "accepted": live_ok})
        if not live_ok:
            ok_all = False
    else:
        print(
            json.dumps({"ok": False, "error": "specify --live or --dry-run-batch"}),
            file=sys.stderr,
        )
        return 2

    if ok_all:
        merge_cmd = [
            PY,
            str(MERGE_SCRIPT),
            "--target",
            str(target_csv),
            "--batch",
            str(batch_csv),
        ]
        nodes.append(_run(merge_cmd, env=child_env))
        if not nodes[-1]["ok"]:
            ok_all = False
        else:
            from scripts.bigset_agent_bridge_v1 import _wrap_markdown

            _wrap_markdown(target_csv, md_out, topic_slug=slug, mode="live_accumulate")
            nodes.append({"step": "markdown_wrapper", "ok": True, "path": str(md_out)})

    if ok_all and not args.skip_ingest:
        ingest_cmd = [PY, str(INGEST_CHAIN), "--skip-bridge", "--topic-slug", slug]
        if args.free_tier:
            ingest_cmd.append("--free-tier")
        if args.free_tier_mode:
            ingest_cmd.extend(["--free-tier-mode", args.free_tier_mode])
        nodes.append(_run(ingest_cmd, env=child_env))
        if not nodes[-1]["ok"]:
            ok_all = False

    completion = {
        "schema": "bigset_live_row_accumulate_chain_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": "HOLD",
        "quality_ok": ok_all,
        "exit_code": 0 if ok_all else 1,
        "mode": "live" if args.live else "dry_run_batch",
        "memory_note": "rows=1 remote LLM; no Ollama large-ctx required",
        "free_tier_profile": free_profile,
        "paths": {
            "target_csv": target_csv.relative_to(ROOT).as_posix(),
            "batch_csv": batch_csv.relative_to(ROOT).as_posix(),
            "accumulate_artifact": "docs/final/artifacts/bigset_tier0_csv_accumulate_v1_latest.json",
            "ingest_report": "reports/bigset_ingest_spike_chain_v1_latest.json",
        },
        "nodes": nodes,
        "reproduce_dry": (
            "py scripts/run_bigset_live_row_accumulate_chain_v1.py "
            "--dry-run-batch tests/fixtures/bigset/atypical_island_demo_tier0_v1.csv"
        ),
        "reproduce_live": (
            "powershell -File scripts\\Invoke-BigSetFreeTierStart_v1.ps1  # then "
            "py scripts/run_bigset_live_row_accumulate_chain_v1.py --live --free-tier --rows 1"
        ),
    }

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_ARTIFACT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": ok_all, "report": str(OUT_REPORT), "target_csv": str(target_csv)},
            ensure_ascii=False,
        )
    )
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
