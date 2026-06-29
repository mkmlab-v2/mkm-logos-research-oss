#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-shot: resolve IWS v2 seed + render mkmlife / personadiary / no1kmedi."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESOLVE = ROOT / "scripts" / "resolve_integrated_wellness_solution_v2.py"
RENDER = ROOT / "scripts" / "render_integrated_wellness_solution_v2.py"
DEFAULT_SEED = (
    ROOT
    / "docs"
    / "final"
    / "artifacts"
    / "fixtures"
    / "integrated_wellness_solution_v2_minor_soeum_abdomen_seed.example.json"
)


def _run(cmd: list[str]) -> None:
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if cp.returncode != 0:
        raise RuntimeError(cp.stderr or cp.stdout or f"failed: {cmd}")


def main() -> int:
    parser = argparse.ArgumentParser(description="IWS v2 resolve + 3-domain render chain")
    parser.add_argument("--seed-json", type=Path, default=DEFAULT_SEED)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=ROOT / "reports" / "integrated_wellness_solution_v2_chain",
    )
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args()

    out_dir = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    resolved_path = out_dir / "resolved_latest.json"
    resolve_cmd = [
        sys.executable,
        str(RESOLVE),
        "--in-json",
        str(args.seed_json),
        "--out-json",
        str(resolved_path),
    ]
    if args.validate:
        resolve_cmd.append("--validate")
    _run(resolve_cmd)

    exports: dict[str, str] = {}
    for target in ("mkmlife", "personadiary", "no1kmedi"):
        out_path = out_dir / f"render_{target}_latest.json"
        _run(
            [
                sys.executable,
                str(RENDER),
                "--in-json",
                str(resolved_path),
                "--target",
                target,
                "--out-json",
                str(out_path),
            ]
        )
        try:
            exports[target] = str(out_path.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            exports[target] = str(out_path.resolve())

    def _rel_or_abs(p: Path) -> str:
        try:
            return str(p.relative_to(ROOT)).replace("\\", "/")
        except ValueError:
            return str(p.resolve())

    summary = {
        "ok": True,
        "seed": _rel_or_abs(args.seed_json),
        "resolved": _rel_or_abs(resolved_path),
        "exports": exports,
    }
    summary_path = out_dir / "chain_summary_latest.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
