#!/usr/bin/env python3
"""Myeongni research studio smoke chain: offline TS + pytest + optional HTTP API."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NO1K = ROOT / "projects" / "no1kmedi"
OUT = ROOT / "reports/myeongni_studio_smoke_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], *, cwd: Path | None = None, env: dict[str, str] | None = None) -> tuple[int, str]:
    print("+", " ".join(cmd), flush=True)
    merged = {**os.environ, **(env or {})}
    cp = subprocess.run(
        cmd,
        cwd=str(cwd or ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=merged,
        shell=sys.platform == "win32",
    )
    tail_lines = (cp.stdout or "").strip().splitlines() + (cp.stderr or "").strip().splitlines()
    tail = tail_lines[-3:] if len(tail_lines) > 3 else tail_lines
    return cp.returncode, " | ".join(tail) if tail else ""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-http", action="store_true", help="skip dev-server API smokes")
    ap.add_argument("--base-url", default=os.environ.get("NO1KMEDI_BASE_URL", "http://127.0.0.1:3020"))
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    ws = str(ROOT)
    http_env = {"MKM_WORKSPACE_ROOT": ws, "NO1KMEDI_BASE_URL": args.base_url.rstrip("/")}

    steps: list[dict] = []
    chain: list[tuple[str, list[str], Path | None, dict[str, str] | None]] = [
        (
            "ts_offline_smoke",
            ["npx", "--yes", "tsx", "scripts/smoke-myeongni-path-mindmap-v1.ts"],
            NO1K,
            None,
        ),
        (
            "pytest_contract",
            [
                sys.executable,
                "-m",
                "pytest",
                "tests/test_myeongni_path_mindmap_v1.py",
                "-k",
                "not studio_smoke_chain",
                "-q",
            ],
            ROOT,
            None,
        ),
    ]
    if not args.skip_http:
        for step_id, npm_script in (
            ("http_studio_mindmap", "smoke:myeongni-studio-mindmap"),
            ("http_full_report", "smoke:myeongni-studio-full-report"),
        ):
            chain.append(
                (
                    step_id,
                    ["npm", "run", npm_script],
                    NO1K,
                    http_env,
                )
            )

    ok = True
    for step_id, cmd, cwd, env in chain:
        code, tail = _run(cmd, cwd=cwd, env=env)
        steps.append({"id": step_id, "exit_code": code, "ok": code == 0, "tail": tail})
        ok = ok and code == 0
        if code != 0:
            break

    report = {
        "schema": "myeongni_studio_smoke_chain_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "non_gating": True,
        "lens": "myeongni",
        "ok": ok,
        "steps": steps,
        "artifacts": {
            "schema": "docs/final/artifacts/myeongni_path_mindmap_schema_v1.json",
            "studio_path": "/myeongni-research/studio",
        },
        "reproduce": (
            f"py scripts/run_myeongni_studio_smoke_chain_v1.py"
            + (" --skip-http" if args.skip_http else "")
        ),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "steps": len(steps), "out": str(args.out)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
