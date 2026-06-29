#!/usr/bin/env python3
"""Build interpret SFT v5: v4 copy + calibration30 wording-sweep train augment (B-track)."""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

V4_TRAIN = ROOT / "data/training/myeongri_interpret_sft_v4/train.jsonl"
V4_EVAL = ROOT / "data/training/myeongri_interpret_sft_v4/locked_eval.jsonl"
V5_DIR = ROOT / "data/training/myeongri_interpret_sft_v5"
DEFAULT_CAL30 = ROOT / "reports/myeongri_interpret_v4_human_review_calibration30_latest.json"
DEFAULT_REPORT = ROOT / "reports/myeongri_interpret_sft_v5_wording_overlay_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8-sig").splitlines() if l.strip()]


def _envelope_from_swept_insight(base_out: dict, insight: str) -> dict:
    env = dict(base_out)
    env["mkm_advanced_insight"] = insight
    env["method_id"] = "wording_sweep_augment_v1"
    return env


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--calibration30-json", type=Path, default=DEFAULT_CAL30)
    ap.add_argument("--v4-train", type=Path, default=V4_TRAIN)
    ap.add_argument("--v4-eval", type=Path, default=V4_EVAL)
    ap.add_argument("--v5-dir", type=Path, default=V5_DIR)
    ap.add_argument("--report-json", type=Path, default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not args.v4_train.is_file() or not args.v4_eval.is_file():
        print(json.dumps({"ok": False, "error": "missing v4 sft jsonl"}))
        return 2
    if not args.calibration30_json.is_file():
        print(json.dumps({"ok": False, "error": "missing calibration30"}))
        return 2

    args.v5_dir.mkdir(parents=True, exist_ok=True)
    v5_train = args.v5_dir / "train.jsonl"
    v5_eval = args.v5_dir / "locked_eval.jsonl"
    shutil.copy2(args.v4_train, v5_train)
    shutil.copy2(args.v4_eval, v5_eval)

    eval_rows = _load_jsonl(v5_eval)
    cal = json.loads(args.calibration30_json.read_text(encoding="utf-8"))
    augment_rows: list[dict] = []
    for s in cal.get("samples") or []:
        if not s.get("wording_sweep_applied_at_utc"):
            continue
        ri = int(s["row_index"])
        if ri < 1 or ri > len(eval_rows):
            continue
        src = eval_rows[ri - 1]
        gold = json.loads(str(src.get("output", "{}")))
        insight = str(s.get("mkm_advanced_insight") or "")
        if not insight:
            continue
        env = _envelope_from_swept_insight(gold, insight)
        augment_rows.append(
            {
                "instruction": src["instruction"],
                "output": json.dumps(env, ensure_ascii=False, separators=(",", ":")),
                "augment_meta_v1": {
                    "source_row_index": ri,
                    "source": "calibration30_wording_sweep",
                },
            }
        )

    with v5_train.open("a", encoding="utf-8") as fout:
        for row in augment_rows:
            fout.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "schema": "myeongri_interpret_sft_v5_wording_overlay_v1",
        "generated_at_utc": _utc_now(),
        "hypothesis_tier": "B",
        "research_only": True,
        "v5_train": str(v5_train.relative_to(ROOT)).replace("\\", "/"),
        "v5_eval": str(v5_eval.relative_to(ROOT)).replace("\\", "/"),
        "v4_train_rows": len(_load_jsonl(args.v4_train)),
        "augment_rows_appended": len(augment_rows),
        "locked_eval_unchanged": True,
        "adapter_out_suggested": "storage/adapters/myeongri_interpret_lora_v0/run_interpret_v5_wording_sweep_s100",
        "track_wall": {"track_a_live_auto_merge": False},
    }
    args.report_json.parent.mkdir(parents=True, exist_ok=True)
    args.report_json.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    status_path = ROOT / "reports/myeongri_interpret_harness_v3_v4_status_latest.json"
    if status_path.is_file():
        status = json.loads(status_path.read_text(encoding="utf-8"))
        v4 = status.setdefault("v4_variant_sft", {})
        v4["v5_wording_sweep_prep"] = {
            "status": "prep_ready",
            "sft_v5_train": report["v5_train"],
            "augment_rows_appended": len(augment_rows),
            "shadow_report": "reports/myeongri_interpret_v4_wording_sweep_shadow_latest.json",
            "train_command": "Run-MyeongriInterpretV5WordingSweepPrepChain_v1.ps1 -RunTrain",
            "inference_flag": "wording_sweep_v1 on _try_parse_envelope (opt-in)",
        }
        status["generated_at_utc"] = _utc_now()
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps({"ok": True, "augment_rows": len(augment_rows), "out": str(args.report_json)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
