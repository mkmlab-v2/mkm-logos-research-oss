#!/usr/bin/env python3
"""Diagnose two-track submission prerequisite gaps."""

from __future__ import annotations

import argparse
import json
import re
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


def _parse_python_refs_from_chain(path: Path) -> list[str]:
    if not path.is_file():
        return []
    text = path.read_text(encoding="utf-8")
    refs = re.findall(r'scripts/([A-Za-z0-9_.-]+\.py)', text)
    seen: set[str] = set()
    ordered: list[str] = []
    for r in refs:
        if r in seen:
            continue
        seen.add(r)
        ordered.append(r)
    return ordered


def parse_args() -> argparse.Namespace:
    repo_root_default = Path(__file__).resolve().parents[1]
    p = argparse.ArgumentParser(description="Check two-track submission prerequisites and chain script coverage.")
    p.add_argument("--repo-root", type=Path, default=repo_root_default)
    p.add_argument(
        "--out",
        type=Path,
        default=Path("docs/final/artifacts/two_track_submission_prereq_check_latest.json"),
    )
    p.add_argument("--strict", action="store_true", help="Exit 2 if required artifacts are missing.")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = args.repo_root.resolve()
    out_path = args.out if args.out.is_absolute() else (repo_root / args.out)

    required = [
        _item("falsification_suite", repo_root / "docs/final/artifacts/two_track_falsification_suite_latest.json"),
        _item("benchmark_comparison", repo_root / "docs/final/artifacts/two_track_benchmark_comparison_latest.json"),
        _item(
            "statistical_significance",
            repo_root / "docs/final/artifacts/two_track_statistical_significance_report_latest.json",
        ),
        _item("raw_oos_readiness", repo_root / "docs/final/artifacts/two_track_raw_oos_readiness_latest.json"),
        _item("public_safe_report", repo_root / "docs/final/artifacts/two_track_public_safe_report_latest.json"),
    ]
    missing_required = [x["name"] for x in required if not bool(x.get("exists", False))]

    chain_path = repo_root / "scripts/run_aramaic_mvp_chain_v1.ps1"
    py_refs = _parse_python_refs_from_chain(chain_path)
    chain_missing = []
    for rel in py_refs:
        p = repo_root / "scripts" / rel
        if not p.is_file():
            chain_missing.append({"script": f"scripts/{rel}", "exists": False})

    out_doc = {
        "schema": "two_track_submission_prereq_check_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "promotion_required": True,
        "source_track": "K",
        "required_artifacts": required,
        "chain_scan": {
            "chain_script": str(chain_path),
            "python_script_refs_count": len(py_refs),
            "missing_python_refs_count": len(chain_missing),
            "missing_python_refs": chain_missing,
        },
        "gates": {
            "required_artifacts_ready": len(missing_required) == 0,
            "chain_python_refs_ready": len(chain_missing) == 0,
            "missing_required_artifacts": missing_required,
        },
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(out_path))

    if args.strict and missing_required:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

