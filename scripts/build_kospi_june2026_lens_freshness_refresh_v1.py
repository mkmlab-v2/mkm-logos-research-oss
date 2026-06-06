#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Refresh static myeongni/sasang lenses from manseryeok JSONL + audit [HYPO][research_only]."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

MYEONGNI_JSONL = ROOT / "data/myeongni/myeongni_16_state_experiment_v1.manseryeok_session_30y_v1.jsonl"
SASANG_JSONL = ROOT / "data/sasang/sasang_dynamics_regime_mapping_v1.manseryeok_session_30y_v1.jsonl"
MYEONGNI_OUT = ROOT / "docs/final/artifacts/myeongni_independent_lens_latest.json"
SASANG_OUT = ROOT / "docs/final/artifacts/sasang_independent_lens_latest.json"
SHADOW_MYEONGNI = ROOT / "reports/kospi_june2026_myeongni_lens_refresh_shadow_v1.json"
SHADOW_SASANG = ROOT / "reports/kospi_june2026_sasang_lens_refresh_shadow_v1.json"
DEFAULT_OUT = ROOT / "reports/kospi_june2026_lens_freshness_refresh_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _lens_meta(path: Path) -> dict[str, Any]:
    doc = _read_json(path)
    prov = doc.get("provenance") if isinstance(doc.get("provenance"), dict) else {}
    scores = doc.get("scores") if isinstance(doc.get("scores"), dict) else {}
    direction = doc.get("direction")
    if direction is None and scores.get("direction_score") is not None:
        ds = float(scores["direction_score"])
        direction = "bull" if ds > 0.05 else "bear" if ds < -0.05 else "neutral"
    return {
        "path": str(path).replace("\\", "/"),
        "direction": direction,
        "score": scores.get("direction_score"),
        "generated_at_utc": doc.get("ts_utc") or doc.get("generated_at_utc"),
        "source_row_ts_utc": prov.get("row_ts_utc") or prov.get("source_row_ts_utc"),
        "source_jsonl": prov.get("input_path") or prov.get("source_jsonl"),
    }


def _run_py(script: str, *args: str) -> int:
    cmd = [sys.executable, str(ROOT / script), *args]
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.stdout.strip():
        print(proc.stdout.strip())
    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)
    return int(proc.returncode)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--skip-write-artifacts", action="store_true", help="Shadow copies only")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args(argv)

    before = {"myeongni": _lens_meta(MYEONGNI_OUT), "sasang": _lens_meta(SASANG_OUT)}

    myeongni_out = SHADOW_MYEONGNI if args.skip_write_artifacts else MYEONGNI_OUT
    sasang_out = SHADOW_SASANG if args.skip_write_artifacts else SASANG_OUT

    steps: list[dict[str, Any]] = []
    rc_m = _run_py(
        "scripts/run_lens_myeongni.py",
        "--experiment-jsonl",
        str(MYEONGNI_JSONL),
        "--output",
        str(myeongni_out),
    )
    steps.append({"step": "run_lens_myeongni", "exit_code": rc_m, "output": str(myeongni_out)})

    rc_s = _run_py(
        "scripts/run_lens_sasang.py",
        "--input-jsonl",
        str(SASANG_JSONL),
        "--output",
        str(sasang_out),
    )
    steps.append({"step": "run_lens_sasang", "exit_code": rc_s, "output": str(sasang_out)})

    if not args.skip_write_artifacts and rc_m == 0 and rc_s == 0:
        SHADOW_MYEONGNI.write_text(MYEONGNI_OUT.read_text(encoding="utf-8"), encoding="utf-8")
        SHADOW_SASANG.write_text(SASANG_OUT.read_text(encoding="utf-8"), encoding="utf-8")

    after = {
        "myeongni": _lens_meta(myeongni_out if myeongni_out.is_file() else MYEONGNI_OUT),
        "sasang": _lens_meta(sasang_out if sasang_out.is_file() else SASANG_OUT),
    }

    doc = {
        "schema": "kospi_june2026_lens_freshness_refresh_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "auto_apply": False,
        "input_jsonl": {
            "myeongni": str(MYEONGNI_JSONL).replace("\\", "/"),
            "sasang": str(SASANG_JSONL).replace("\\", "/"),
        },
        "before": before,
        "after": after,
        "steps": steps,
        "ok": rc_m == 0 and rc_s == 0,
        "verdict_ko": "manseryeok_session JSONL tail로 static lens 갱신 — June blend 입력 신선도 shadow. 캘린더 apply 없음.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.output.resolve()} ok={doc['ok']}")
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
