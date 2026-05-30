#!/usr/bin/env python3
"""Close Logos edge-hypothesis LoRA research round ([HYPO] B-track).

Rolls up train-entry, micro-train, sample-infer, and live showroom verify.
Does NOT merge canonical edges or touch Track A / live trading.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs/final/artifacts/logos_edge_hypothesis_sft_manifest_v1_latest.json"
DEFAULT_MICRO = ROOT / "reports/logos_edge_hypothesis_microtrain_v1_latest.json"
DEFAULT_SAMPLE = ROOT / "reports/logos_edge_hypothesis_microtrain_sample_infer_v1_latest.json"
DEFAULT_OUT = ROOT / "reports/logos_edge_hypothesis_lora_round_closure_v1_latest.json"
VERIFY = ROOT / "scripts/_auto_verify_oracle_sphere_showroom_v1.py"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def _run_showroom_verify() -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(
        [sys.executable, str(VERIFY)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=120,
    )
    tail = (proc.stdout or "").strip()
    doc: dict[str, Any] = {}
    if tail:
        try:
            doc = json.loads(tail)
        except json.JSONDecodeError:
            doc = {"parse_error": True, "raw_tail": tail[-500:]}
    return int(proc.returncode), doc


def build_closure(
    *,
    manifest: dict[str, Any],
    micro: dict[str, Any],
    sample: dict[str, Any],
    showroom: dict[str, Any],
    showroom_exit: int,
) -> dict[str, Any]:
    rank_pass = 0
    rank_total = 0
    for row in sample.get("samples") or []:
        scores = row.get("scores") or {}
        if "rank_match" in scores:
            rank_total += 1
            if scores.get("rank_match"):
                rank_pass += 1

    checks = {
        "train_entry_rows_ok": int(manifest.get("row_count") or 0) >= 1,
        "microtrain_smoke_ok": micro.get("microtrain_smoke_ok") is True,
        "sample_format_smoke_ok": sample.get("overall_format_smoke_ok") is True,
        "showroom_untouched_ok": showroom.get("overall_ok") is True and showroom_exit == 0,
    }
    closure_ok = all(checks.values())
    walls = {"merge_to_canonical_allowed": False}

    return {
        "schema": "logos_edge_hypothesis_lora_round_closure_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "non_gating": True,
        "lora_round_closed": closure_ok,
        "closure_ok": closure_ok,
        "checks": checks,
        "walls": walls,
        "artifacts": {
            "sft_manifest": manifest.get("jsonl_path"),
            "microtrain_report": "reports/logos_edge_hypothesis_microtrain_v1_latest.json",
            "sample_infer_report": "reports/logos_edge_hypothesis_microtrain_sample_infer_v1_latest.json",
            "adapter_dir": micro.get("adapter_out"),
            "microtrain_max_steps": micro.get("max_steps"),
        },
        "sample_infer_summary": {
            "format_smoke_pass_count": sample.get("format_smoke_pass_count"),
            "sample_count": sample.get("sample_count"),
            "rank_match_pass_count": rank_pass,
            "rank_match_total": rank_total,
            "rank_accuracy": (rank_pass / rank_total) if rank_total else None,
        },
        "showroom_verify": {
            "overall_ok": showroom.get("overall_ok"),
            "exit_code": showroom_exit,
            "origin": showroom.get("origin"),
        },
        "recommended_next_ko": [
            "human review queue triage (canonical merge는 휴먼 signoff 후만)",
            "선택: step 100 micro-train + rank 정확도 재측정",
            "쇼룸 q01–q08과 LoRA 어댑터 자동 합선 금지 유지",
        ],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest-json", type=Path, default=DEFAULT_MANIFEST)
    ap.add_argument("--micro-report", type=Path, default=DEFAULT_MICRO)
    ap.add_argument("--sample-report", type=Path, default=DEFAULT_SAMPLE)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-showroom-verify", action="store_true")
    args = ap.parse_args()

    manifest = _read_json(args.manifest_json if args.manifest_json.is_absolute() else ROOT / args.manifest_json)
    micro = _read_json(args.micro_report if args.micro_report.is_absolute() else ROOT / args.micro_report)
    sample = _read_json(args.sample_report if args.sample_report.is_absolute() else ROOT / args.sample_report)

    showroom_exit = 0
    showroom: dict[str, Any] = {"overall_ok": None, "skipped": True}
    if not args.skip_showroom_verify:
        showroom_exit, showroom = _run_showroom_verify()
        showroom["skipped"] = False

    doc = build_closure(
        manifest=manifest,
        micro=micro,
        sample=sample,
        showroom=showroom,
        showroom_exit=showroom_exit,
    )
    out = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["closure_ok"], "out": str(out), "lora_round_closed": doc["lora_round_closed"]}))
    return 0 if doc["closure_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
