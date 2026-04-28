#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def resolve(path_str: str) -> Path:
    p = Path(path_str)
    return p if p.is_absolute() else ROOT / p


def load(path: Path) -> dict[str, Any]:
    obj = json.loads(path.read_text(encoding="utf-8"))
    return obj if isinstance(obj, dict) else {}


def main() -> int:
    ap = argparse.ArgumentParser(description="Build one-page submission checklist artifact.")
    ap.add_argument("--kdd-template-json", default="docs/final/artifacts/two_track_kdd_submission_template_latest.json")
    ap.add_argument("--checklist-json", default="docs/final/artifacts/two_track_submission_checklist_latest.json")
    ap.add_argument("--freeze-json", default="docs/final/artifacts/two_track_submission_freeze_latest.json")
    ap.add_argument("--go-nogo-json", default="docs/final/artifacts/two_track_submission_go_nogo_latest.json")
    ap.add_argument("--boundary-json", default="docs/final/artifacts/two_track_falsification_boundary_report_latest.json")
    ap.add_argument("--output-json", default="docs/final/artifacts/two_track_submission_onepager_latest.json")
    args = ap.parse_args()

    kp = resolve(args.kdd_template_json)
    cp = resolve(args.checklist_json)
    fp = resolve(args.freeze_json)
    gp = resolve(args.go_nogo_json)
    bp = resolve(args.boundary_json)
    for p in (kp, cp, fp, gp, bp):
        if not p.is_file():
            raise SystemExit(f"missing required input: {p}")

    kdd = load(kp)
    checklist = load(cp)
    freeze = load(fp)
    go = load(gp)
    boundary = load(bp)
    bsum = boundary.get("boundary_summary") if isinstance(boundary.get("boundary_summary"), dict) else {}

    out = {
        "schema": "two_track_submission_onepager_v1",
        "generated_at_utc": now(),
        "track": "kdd_applied_data_science",
        "submission_candidate_label": "submission_candidate_v1",
        "status": {
            "go_nogo": go.get("decision"),
            "submission_ready": checklist.get("submission_ready"),
            "freeze_stamp": freeze.get("freeze_stamp"),
        },
        "form_copy_paste": {
            "title_en": kdd.get("title_en"),
            "abstract_en_180w": kdd.get("abstract_en_180w"),
            "keywords_en": kdd.get("keywords_en"),
            "contributions_en": kdd.get("contributions_en"),
        },
        "evidence_packet": [
            "docs/final/artifacts/two_track_submission_checklist_latest.json",
            "docs/final/artifacts/two_track_submission_freeze_latest.json",
            "docs/final/artifacts/two_track_submission_go_nogo_latest.json",
        ],
        "rebuttal_quick_facts": {
            "max_safe_min_survivor_count": bsum.get("max_safe_min_survivor_count"),
            "min_break_min_survivor_count": bsum.get("min_break_min_survivor_count"),
            "first_non_pass_row": bsum.get("first_non_pass_row"),
        },
        "final_smoke_commands": [
            "powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_two_track_submission_pack_v1.ps1 -StrictPrereqs",
            "py scripts/build_two_track_submission_go_nogo_v1.py",
        ],
    }

    op = resolve(args.output_json)
    op.parent.mkdir(parents=True, exist_ok=True)
    op.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(op))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

