#!/usr/bin/env python3
"""Promote B-track ablation artifacts to C:\\workspace (whitelisted copy only).

Does NOT bulk-overwrite unrelated *_latest.json.

  py scripts/run_sasang_ablation_promote_to_workspace_v1.py --workspace-root C:/workspace
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXP = ROOT / "experiments" / "sasang-head-btrack"
DEFAULT_WS = Path(r"C:\workspace")

COPY_MAP: list[tuple[Path, Path]] = [
    (
        EXP / "artifacts/ijeoma_pyobyeong_insight_cards_v1_ablation_latest.json",
        Path("docs/final/artifacts/sasang_pyobyeong_insight_cards_v1_latest.json"),
    ),
    (
        EXP / "research/IJEOMA_PYOBYEONG_BYEONGJEUNG_LIT_REVIEW_v1.md",
        Path("docs/research/IJEOMA_PYOBYEONG_BYEONGJEUNG_LIT_REVIEW_v1.md"),
    ),
    (
        EXP / "research/raw/PYOBYEONG_SASIM_SINMUL_DR_TIER0_20260629.md",
        Path("docs/research/raw/PYOBYEONG_SASIM_SINMUL_DR_TIER0_20260629.md"),
    ),
    (
        EXP / "artifacts/sasang_pyobyeong_promotion_paper_verdict_v1.json",
        Path("docs/final/artifacts/sasang_pyobyeong_promotion_paper_verdict_v1_latest.json"),
    ),
    (
        EXP / "CHARTER_AMENDMENT_DRAFT_v1.md",
        Path("docs/final/artifacts/sasang_ablation_charter_amendment_draft_v1.md"),
    ),
    (
        ROOT / "reports/sasang_ablation_matrix_signoff_v1.json",
        Path("reports/sasang_ablation_matrix_signoff_v1_latest.json"),
    ),
]

SCRIPT_COPY = [
    ("scripts/build_ijeoma_pyobyeong_dr_pack_v1.py", "scripts/build_ijeoma_pyobyeong_dr_pack_v1.py"),
    ("scripts/run_ijeoma_pyobyeong_query_set_v1.py", "scripts/run_ijeoma_pyobyeong_query_set_v1.py"),
    ("scripts/run_sasang_dynamics_unified_adapter_v1.py", "scripts/run_sasang_dynamics_unified_adapter_v1.py"),
    ("scripts/run_sasang_ablation_promotion_gate_v1.py", "scripts/run_sasang_ablation_promotion_gate_v1.py"),
    ("scripts/run_sasang_ablation_promote_to_workspace_v1.py", "scripts/run_sasang_ablation_promote_to_workspace_v1.py"),
    (
        "experiments/sasang-head-btrack/sasang_dynamics_unified_adapter_v1.py",
        "experiments/sasang-head-btrack/sasang_dynamics_unified_adapter_v1.py",
    ),
    (
        "experiments/sasang-head-btrack/sasang_core_engine.mdc",
        "experiments/sasang-head-btrack/sasang_core_engine.mdc",
    ),
]

TEST_COPY = [
    "tests/test_ijeoma_pyobyeong_dr_pack_v1.py",
    "tests/test_sasang_dynamics_unified_adapter_v1.py",
    "tests/test_sasang_ablation_promotion_gate_v1.py",
]


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def promote(ws: Path, *, dry_run: bool) -> dict:
    copied: list[str] = []
    missing: list[str] = []
    for src_rel_root, dst_rel in COPY_MAP:
        src = src_rel_root if src_rel_root.is_absolute() else ROOT / src_rel_root
        if not src.is_file():
            missing.append(str(src))
            continue
        dst = ws / dst_rel
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        copied.append(str(dst_rel).replace("\\", "/"))

    for src_rel, dst_rel in SCRIPT_COPY:
        src = ROOT / src_rel
        if not src.is_file():
            missing.append(src_rel)
            continue
        dst = ws / dst_rel
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        copied.append(dst_rel.replace("\\", "/"))

    for rel in TEST_COPY:
        src = ROOT / rel
        if not src.is_file():
            missing.append(rel)
            continue
        dst = ws / rel
        if not dry_run:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        copied.append(rel.replace("\\", "/"))

    return {"copied": copied, "missing": missing, "dry_run": dry_run}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace-root", type=Path, default=DEFAULT_WS)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--rebuild-interpretive", action="store_true")
    args = ap.parse_args()
    ws = args.workspace_root.resolve()

    signoff = ROOT / "reports/sasang_ablation_matrix_signoff_v1.json"
    if signoff.is_file():
        doc = json.loads(signoff.read_text(encoding="utf-8"))
        if not doc.get("promotion_ready"):
            print(json.dumps({"ok": False, "error": "signoff promotion_ready false"}))
            return 1

    result = promote(ws, dry_run=args.dry_run)
    report_path = EXP / "artifacts/sasang_ablation_workspace_promote_v1_latest.json"
    payload = {
        "schema": "sasang_ablation_workspace_promote_v1",
        "generated_at_utc": _utc(),
        "workspace_root": str(ws).replace("\\", "/"),
        **result,
    }
    if not args.dry_run:
        report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if args.rebuild_interpretive:
            build = ws / "scripts/build_sasang_interpretive_insight_bundle_v1.py"
            if build.is_file():
                cp = subprocess.run([sys.executable, str(build)], cwd=str(ws), capture_output=True, text=True)
                payload["interpretive_bundle_exit_code"] = cp.returncode
                if cp.returncode != 0:
                    print(json.dumps({"ok": False, "interpretive_build": cp.stderr[-400:]}))
                    return cp.returncode

    print(json.dumps({"ok": not result["missing"], **payload}, ensure_ascii=False))
    return 0 if not result["missing"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
