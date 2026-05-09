#!/usr/bin/env python3
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
ART = ROOT / "docs" / "final" / "artifacts"
DEFAULT_OUT_DIR = ART / "myeongni_stage2_realset"
DEFAULT_SUMMARY = ART / "myeongni_stage2_realset_build_summary_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str], env: dict[str, str]) -> None:
    subprocess.run(cmd, cwd=ROOT, env=env, check=True, capture_output=True, text=True)


def _birth_grid() -> list[tuple[int, int, int, int]]:
    years = [1969, 1973, 1978, 1984, 1991, 1997, 2000, 2004, 2009, 2012]
    months = [1, 3, 5, 7, 9, 11]
    days = [3, 10, 17, 24]
    hours = [0, 4, 8, 12, 16, 20]
    out: list[tuple[int, int, int, int]] = []
    for y in years:
        for m in months:
            for d in days:
                for h in hours:
                    out.append((y, m, d, h))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Build stage2 myeongni realset artifacts (mkm_myeongni_response_v2) from birth-grid.")
    ap.add_argument("--target-count", type=int, default=60)
    ap.add_argument("--profile", choices=("conservative", "balanced", "attack"), default="balanced")
    ap.add_argument("--track", choices=("A", "B"), default="B")
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY)
    args = ap.parse_args()

    out_dir = args.out_dir if args.out_dir.is_absolute() else ROOT / args.out_dir
    summary_out = args.summary_json if args.summary_json.is_absolute() else ROOT / args.summary_json
    out_dir.mkdir(parents=True, exist_ok=True)

    target = max(1, int(args.target_count))
    created: list[str] = []
    failures: list[dict[str, Any]] = []
    lens_tmp = out_dir / "_tmp_lens.json"
    grid = _birth_grid()
    idx = 0
    for (y, m, d, h) in grid:
        if len(created) >= target:
            break
        idx += 1
        birth_env = f"{y},{m},{d},{h}"
        out_file = out_dir / f"mkm_myeongni_response_v2_realset_{idx:04d}_{y:04d}{m:02d}{d:02d}_{h:02d}.json"
        env = os.environ.copy()
        env["MYEONGNI_RECOMMENDED_BIRTH"] = birth_env
        try:
            _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "run_lens_myeongni.py"),
                    "--recommended",
                    "--emit-schema",
                    "v1",
                    "--allow-fallback",
                    "--output",
                    str(lens_tmp),
                ],
                env=env,
            )
            _run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "build_mkm_myeongni_response_v2.py"),
                    "--profile",
                    args.profile,
                    "--track",
                    args.track,
                    "--lens-json",
                    str(lens_tmp),
                    "--output-json",
                    str(out_file),
                ],
                env=env,
            )
            created.append(str(out_file.resolve()))
        except Exception as e:
            failures.append({"birth": birth_env, "error": str(e)})

    if lens_tmp.exists():
        try:
            lens_tmp.unlink()
        except OSError:
            pass

    summary = {
        "schema": "myeongni_stage2_realset_build_summary_v1",
        "generated_at_utc": _now(),
        "target_count": target,
        "created_count": len(created),
        "failed_count": len(failures),
        "profile": args.profile,
        "track": args.track,
        "out_dir": str(out_dir.resolve()),
        "created_files": created,
        "failures": failures[:20],
    }
    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "created_count": len(created), "failed_count": len(failures), "summary": str(summary_out)}, ensure_ascii=False))
    return 0 if len(created) >= target else 1


if __name__ == "__main__":
    raise SystemExit(main())
