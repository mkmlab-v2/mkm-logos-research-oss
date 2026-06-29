#!/usr/bin/env python3
"""Fuse MISSION_LOG ops-memory experiments + web_ops live CDP ([HYPO] B-track).

Stacks (when artifacts/paths exist):
  1) optional live CDP capture (port 9222)
  2) web_ops full bundle + pointer baseline sync
  3) ops_memory web_ops JSON overlay
  4) retrieval bench (raw / repair_v2 / coordinate_v1)
  5) resume pack --lane web_ops [--topic] [--include-slice]
  6) optional meta_layer envelope validate (fixture only)

Not Track A · not live trading · NODE v2 remains HOLD per MISSION_LOG.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _cdp_up(url: str) -> bool:
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/json/version", timeout=2) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def _run(cmd: list[str], *, cwd: Path) -> int:
    print("+", " ".join(cmd), flush=True)
    return subprocess.run(cmd, cwd=str(cwd)).returncode


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace-root", type=Path, default=ROOT)
    ap.add_argument("--cdp-url", default="http://127.0.0.1:9222")
    ap.add_argument("--skip-live-cdp", action="store_true")
    ap.add_argument("--topic", default="Nebius web_ops cost audit")
    ap.add_argument("--include-slice", action="store_true")
    ap.add_argument("--slice-max-chars", type=int, default=480)
    ap.add_argument("--skip-meta-layer", action="store_true")
    ap.add_argument(
        "--parallel-post-overlay",
        action="store_true",
        help="Run bench + resume_pack (+ meta validate) concurrently after overlay.",
    )
    args = ap.parse_args()

    root = args.workspace_root.resolve()
    py = sys.executable
    steps: list[dict[str, object]] = []

    if not args.skip_live_cdp and _cdp_up(args.cdp_url):
        rc = _run(
            [
                py,
                str(root / "scripts/capture_web_ops_regime_cdp_observation_v1.py"),
                "--cdp-url",
                args.cdp_url,
                "--wait-ms",
                "3000",
            ],
            cwd=root,
        )
        steps.append({"step": "cdp_capture", "exit_code": rc})
        if rc == 3:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "note": "auth_wall preserved existing observation; continuing",
                    },
                    ensure_ascii=False,
                )
            )
        elif rc != 0:
            return rc
    else:
        steps.append({"step": "cdp_capture", "skipped": True})

    bundle = [
        py,
        str(root / "scripts/run_web_ops_regime_full_bundle_v1.py"),
        "--seed-baselines",
    ]
    rc = _run(bundle, cwd=root)
    steps.append({"step": "web_ops_bundle", "exit_code": rc})
    if rc != 0:
        print(json.dumps({"ok": False, "steps": steps}, ensure_ascii=False))
        return rc

    rc = _run([py, str(root / "scripts/build_mkm_ops_memory_web_ops_overlay_v1.py")], cwd=root)
    steps.append({"step": "ops_overlay", "exit_code": rc})
    if rc != 0:
        print(json.dumps({"ok": False, "steps": steps}, ensure_ascii=False))
        return rc

    resume_cmd = [
        py,
        str(root / "scripts/build_mkm_chat_resume_pack_v1.py"),
        "--lane",
        "web_ops",
        "--topic",
        args.topic,
        "--slice-max-chars",
        str(args.slice_max_chars),
    ]
    if args.include_slice:
        resume_cmd.append("--include-slice")

    post_jobs: list[tuple[str, list[str]]] = [
        ("retrieval_bench", [py, str(root / "scripts/bench_mkm_ops_memory_web_ops_retrieval_v1.py")]),
        ("resume_pack", resume_cmd),
    ]
    if not args.skip_meta_layer:
        fixture = root / "docs/final/artifacts/fixtures/mkm_meta_layer_turn_envelope_v1.example.json"
        if fixture.is_file():
            post_jobs.append(
                (
                    "meta_layer_fixture_validate",
                    [
                        py,
                        str(root / "scripts/mkm_meta_layer_envelope_v1.py"),
                        "validate",
                        "--json-file",
                        str(fixture),
                    ],
                )
            )
        else:
            steps.append({"step": "meta_layer_fixture_validate", "skipped": True})

    if args.parallel_post_overlay and len(post_jobs) > 1:
        with ThreadPoolExecutor(max_workers=len(post_jobs)) as pool:
            futures = {
                pool.submit(_run, cmd, cwd=root): name for name, cmd in post_jobs
            }
            for fut in as_completed(futures):
                name = futures[fut]
                rc = fut.result()
                steps.append({"step": name, "exit_code": rc, "parallel": True})
                if rc != 0:
                    print(json.dumps({"ok": False, "steps": steps}, ensure_ascii=False))
                    return rc
    else:
        for name, cmd in post_jobs:
            rc = _run(cmd, cwd=root)
            steps.append({"step": name, "exit_code": rc})
            if rc != 0:
                print(json.dumps({"ok": False, "steps": steps}, ensure_ascii=False))
                return rc

    print(
        json.dumps(
            {
                "ok": True,
                "schema": "mkm_ops_memory_web_ops_fusion_v1",
                "research_only": True,
                "topic": args.topic,
                "include_slice": args.include_slice,
                "slice_max_chars": args.slice_max_chars,
                "steps": steps,
                "resume_pack": "docs/final/artifacts/mkm_chat_resume_pack_latest.json",
                "bench": "reports/mkm_ops_memory_web_ops_retrieval_bench_v1_latest.json",
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
