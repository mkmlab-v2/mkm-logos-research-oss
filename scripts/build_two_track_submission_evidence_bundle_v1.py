#!/usr/bin/env python3
"""Build submission evidence bundle checklist from two-track artifacts."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _safe_load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return obj if isinstance(obj, dict) else None


def _extract_generated_at(doc: dict[str, Any] | None) -> str | None:
    if not isinstance(doc, dict):
        return None
    val = doc.get("generated_at_utc")
    if isinstance(val, str) and val.strip():
        return val.strip()
    return None


def _item(name: str, path: Path) -> dict[str, Any]:
    doc = _safe_load_json(path)
    return {
        "name": name,
        "path": str(path),
        "exists": path.is_file(),
        "generated_at_utc": _extract_generated_at(doc),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build two-track submission evidence bundle.")
    repo_root_default = Path(__file__).resolve().parents[1]
    parser.add_argument("--repo-root", type=Path, default=repo_root_default)
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("docs/final/artifacts/two_track_submission_evidence_bundle_latest.json"),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    out_path = args.out if args.out.is_absolute() else (repo_root / args.out)

    readiness_path = repo_root / "docs/final/artifacts/two_track_raw_oos_readiness_latest.json"
    readiness_doc = _safe_load_json(readiness_path) or {}
    readiness_summary = readiness_doc.get("summary") if isinstance(readiness_doc.get("summary"), dict) else {}

    required = [
        _item("falsification_suite", repo_root / "docs/final/artifacts/two_track_falsification_suite_latest.json"),
        _item("benchmark_comparison", repo_root / "docs/final/artifacts/two_track_benchmark_comparison_latest.json"),
        _item(
            "statistical_significance",
            repo_root / "docs/final/artifacts/two_track_statistical_significance_report_latest.json",
        ),
        _item("raw_oos_readiness", readiness_path),
        _item("public_safe_report", repo_root / "docs/final/artifacts/two_track_public_safe_report_latest.json"),
    ]

    missing = [x["name"] for x in required if not bool(x.get("exists", False))]
    ready_for_publication = bool(readiness_summary.get("ready_for_publication_claim", False))
    all_required_present = len(missing) == 0

    out_doc = {
        "schema": "two_track_submission_evidence_bundle_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "required_artifacts": required,
        "gates": {
            "all_required_present": all_required_present,
            "ready_for_publication_claim": ready_for_publication,
            "bundle_ready": all_required_present and ready_for_publication,
            "missing_artifacts": missing,
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
