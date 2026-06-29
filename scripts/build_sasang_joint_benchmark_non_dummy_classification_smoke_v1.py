#!/usr/bin/env python3
"""Non-dummy joint benchmark classification smoke: birth pillar replay [HYPO]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
BENCH = ROOT / "data/myeongni/sasang_saju_joint_benchmark_v1.jsonl"
OUT = ROOT / "reports/sasang_joint_benchmark_non_dummy_classification_smoke_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _is_dummy(row: dict[str, Any]) -> bool:
    pid = str(row.get("person_id") or "")
    disp = str(row.get("display_name") or "")
    if "dummy" in pid.lower() or "dummy" in disp.lower():
        return True
    if "DUMMYCSV" in pid or "DUMMYJSONL" in pid:
        return True
    if "[DUMMY]" in disp:
        return True
    return False


def _run_birth_cli(birth_instant_utc: str, iana_tz: str, is_male: bool) -> dict[str, Any]:
    cmd = [
        PY,
        str(ROOT / "scripts/run_saju_global_birth_v1.py"),
        "--utc-instant",
        birth_instant_utc,
        "--iana-tz",
        iana_tz,
        "--compact",
    ]
    if is_male:
        cmd.append("--is-male")
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "run_saju_global_birth_v1 failed")
    line = (proc.stdout or "").strip()
    if line.startswith("\ufeff"):
        line = line[1:]
    return json.loads(line)


def build(dataset: Path) -> dict[str, Any]:
    rows_out: list[dict[str, Any]] = []
    evaluated = 0
    passed = 0
    non_dummy_total = 0

    if dataset.is_file():
        for line_no, line in enumerate(dataset.read_text(encoding="utf-8").splitlines(), start=1):
            line = line.strip()
            if not line:
                continue
            row = json.loads(line)
            if str(row.get("schema") or "") != "sasang_saju_joint_benchmark_row_v1":
                continue
            if _is_dummy(row):
                continue
            non_dummy_total += 1
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
            stored = (row.get("saju_engine_output_v1") or {}).get("pillars")
            ok = True
            mismatch: list[str] = []
            if isinstance(stored, dict):
                for k in ("year", "month", "day", "hour"):
                    exp = str(stored.get(k) or "")
                    g = str(got.get(k) or "")
                    if exp and exp != g:
                        ok = False
                        mismatch.append(f"{k}: stored={exp!r} got={g!r}")
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

    classification_ok = non_dummy_total >= 1 and evaluated >= 1 and passed == evaluated
    return {
        "schema": "sasang_joint_benchmark_non_dummy_classification_smoke_v1",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "dataset": str(dataset.resolve()).replace("\\", "/"),
        "rows_non_dummy": non_dummy_total,
        "rows_with_birth_evaluated": evaluated,
        "passed": passed,
        "failed": evaluated - passed,
        "classification_ok": classification_ok,
        "rows": rows_out,
        "reproduce": "py scripts/build_sasang_joint_benchmark_non_dummy_classification_smoke_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", type=Path, default=BENCH)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build(args.dataset)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["classification_ok"],
                "rows_non_dummy": doc["rows_non_dummy"],
                "evaluated": doc["rows_with_birth_evaluated"],
            }
        )
    )
    return 0 if doc["classification_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
