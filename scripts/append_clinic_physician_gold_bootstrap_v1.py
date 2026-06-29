"""
Append physician_gold ledger rows with intake sasang_estimate mirrored as bootstrap labels.

[BACKFILL] Not licensed adjudication — replaces withheld rows for offline calibration only.
Use --dry-run first. Does not modify existing JSONL lines.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.clinic_constitution_mvp_ledger_v1 import append_clinic_capture_line  # noqa: E402
from scripts.import_clinic_mvp_from_patient_registry_v1 import (  # noqa: E402
    REGISTRY_REL,
    build_capture_from_intake,
    iter_clinical_encounters,
    resolve_intake_path,
    _load_json,
    _workspace_root,
)

DEFAULT_SLUGS = (
    "baeoksun",
    "park_geumja",
    "park_yeonwoo",
    "kim_haeun",
    "soyoung_choi",
)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Bootstrap physician_gold rows from intake estimate")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--slug", action="append", default=[])
    args = p.parse_args(argv)
    root = _workspace_root()
    registry = _load_json(root / REGISTRY_REL)
    slugs = set(args.slug) if args.slug else set(DEFAULT_SLUGS)

    appended: list[str] = []
    skipped: list[str] = []
    for enc in iter_clinical_encounters(registry):
        slug = str(enc.get("slug") or "")
        if slug not in slugs:
            continue
        intake_path = resolve_intake_path(root, enc)
        if not intake_path or not intake_path.is_file():
            skipped.append(f"{slug}:no_intake")
            continue
        intake_doc = _load_json(intake_path)
        record = build_capture_from_intake(
            intake_doc,
            slug=slug,
            physician_from_estimate=True,
        )
        record["label_lane"] = "physician_gold"
        record["import_meta"] = {
            **(record.get("import_meta") or {}),
            "bootstrap": "physician_gold_from_intake_estimate_v1",
            "not_licensed_adjudication": True,
        }
        if args.dry_run:
            appended.append(str((record.get("encounter") or {}).get("ref_token")))
            continue
        append_clinic_capture_line(root, record, set_ts_if_missing=False)
        appended.append(str((record.get("encounter") or {}).get("ref_token")))

    report = {
        "schema": "clinic_physician_gold_bootstrap_report_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "dry_run": args.dry_run,
        "n_appended": len(appended),
        "ref_tokens": appended,
        "skipped": skipped,
        "research_only": True,
        "operator_hint_ko": "licensed 한의사 확정 후 본 행을 교체·갱신할 것.",
    }
    out = root / "reports/clinic_physician_gold_bootstrap_latest.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
