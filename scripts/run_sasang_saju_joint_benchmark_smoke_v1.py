#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Re-run ``run_saju_global_birth_v1`` for joint rows that carry ``birth_resolution``; compare stored pillars."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATASET = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_v1.jsonl"
DEFAULT_OUT = ROOT / "data" / "myeongni" / "sasang_saju_joint_benchmark_smoke_v1.json"


def _run_birth_cli(birth_instant_utc: str, iana_tz: str, is_male: bool) -> dict[str, Any]:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "run_saju_global_birth_v1.py"),
        "--utc-instant",
        birth_instant_utc,
        "--iana-tz",
        iana_tz,
        "--compact",
    ]
    if is_male:
        cmd.append("--is-male")
    p = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(p.stderr or p.stdout or "run_saju_global_birth_v1 failed")
    line = (p.stdout or "").strip()
    if line.startswith("\ufeff"):
        line = line[1:]
    return json.loads(line)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.dataset.is_file():
        print(json.dumps({"ok": False, "error": "missing dataset"}, ensure_ascii=False))
        return 2

    rows_out: list[dict[str, Any]] = []
    evaluated = 0
    passed = 0

    for line_no, line in enumerate(args.dataset.read_text(encoding="utf-8").splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        if str(row.get("schema") or "") != "sasang_saju_joint_benchmark_row_v1":
            continue
        br = row.get("birth_resolution")
        if not isinstance(br, dict) or not str(br.get("birth_instant_utc") or "").strip():
            rows_out.append(
                {"person_id": row.get("person_id"), "line": line_no, "status": "skipped_no_birth"}
            )
            continue
        evaluated += 1
        pid = str(row.get("person_id") or "")
        try:
            birth = _run_birth_cli(
                str(br.get("birth_instant_utc") or ""),
                str(br.get("iana_tz") or ""),
                bool(br.get("is_male")),
            )
        except Exception as e:
            rows_out.append({"person_id": pid, "line": line_no, "status": "error", "detail": str(e)})
            continue

        saj = birth.get("full_saju", {}).get("saju", {})
        got = {k: str(saj.get(k) or "") for k in ("year", "month", "day", "hour")} if isinstance(saj, dict) else {}
        stored = (row.get("saju_engine_output_v1") or {}).get("pillars") if isinstance(row.get("saju_engine_output_v1"), dict) else None
        ok = True
        mismatch: list[str] = []
        if isinstance(stored, dict):
            for k in ("year", "month", "day", "hour"):
                exp = str(stored.get(k) or "")
                g = str(got.get(k) or "")
                if exp and exp != g:
                    ok = False
                    mismatch.append(f"{k}: stored={exp!r} got={g!r}")
        else:
            ok = True

        if ok:
            passed += 1
            status = "pillar_match_or_no_stored"
        else:
            status = "pillar_mismatch"
        rows_out.append(
            {
                "person_id": pid,
                "line": line_no,
                "status": status,
                "mismatch": mismatch,
                "got_pillars": got,
            }
        )

    summary = {
        "schema": "sasang_saju_joint_benchmark_smoke_v1",
        "dataset": str(args.dataset.resolve()),
        "rows_with_birth_evaluated": evaluated,
        "passed": passed,
        "failed": evaluated - passed,
    }
    doc = {"summary": summary, "rows": rows_out}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if evaluated == 0 or passed == evaluated else 1


if __name__ == "__main__":
    raise SystemExit(main())
