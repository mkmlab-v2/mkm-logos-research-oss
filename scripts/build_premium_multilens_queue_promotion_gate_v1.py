#!/usr/bin/env python3
"""Premium multilens file-queue promotion gate v1 (S1 shadow, B-track).

Runs pytest (optional) + drain + export-pending, then writes a GO/HOLD decision
artifact under docs/final/artifacts/. Exit 1 only on preflight subprocess failure
or invalid pending rows in export snapshot (queue hygiene).

GO means operational contract + queue snapshot OK — not Track A / live trading.
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
STUB = ROOT / "scripts" / "premium_multilens_job_queue_stub_v1.py"
DEFAULT_GATE_OUT = ROOT / "docs" / "final" / "artifacts" / "premium_multilens_queue_promotion_gate_v1_latest.json"
DEFAULT_EXPORT_TMP = ROOT / "reports" / "_premium_multilens_gate_export_tmp_v1.json"
PYTEST_FILES = (
    ROOT / "tests" / "test_premium_btrack_multilens_report_schema_v1.py",
    ROOT / "tests" / "test_build_premium_btrack_multilens_report_v1.py",
    ROOT / "tests" / "test_premium_multilens_job_queue_stub_v1.py",
    ROOT / "tests" / "test_build_premium_multilens_queue_promotion_gate_v1.py",
)

EXPORT_PENDING_SCHEMA = "premium_multilens_queue_pending_export_v0"
GATE_SCHEMA = "premium_multilens_queue_promotion_gate_v1"


def evaluate_pending_export(snap: dict[str, Any]) -> tuple[str, int, int]:
    """Return (decision, exit_code, invalid_pending_count)."""
    if snap.get("schema") != EXPORT_PENDING_SCHEMA:
        raise ValueError("export snapshot wrong schema")
    items = snap.get("pending_items") if isinstance(snap.get("pending_items"), list) else []
    invalid = sum(1 for it in items if isinstance(it, dict) and it.get("validation_ok") is not True)
    n_pending = len(items)
    if invalid:
        return "HOLD_PREMIUM_MULTILENS_QUEUE_INVALID_PENDING", 1, invalid
    return "GO_PREMIUM_MULTILENS_QUEUE_S1_SHADOW", 0, invalid


def posix_rel_best(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def _utc_z() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(argv: list[str], *, cwd: Path) -> int:
    r = subprocess.run(argv, cwd=str(cwd), check=False)
    return int(r.returncode)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT, help="Workspace root (default: repo root).")
    ap.add_argument(
        "--skip-pytest",
        action="store_true",
        help="Skip pytest preflight (use when bundle/CI already ran the same three files).",
    )
    ap.add_argument(
        "--export-temp",
        type=Path,
        default=DEFAULT_EXPORT_TMP,
        help="Temp path for export-pending JSON (default under reports/).",
    )
    ap.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_GATE_OUT,
        help="Gate artifact JSON path.",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    py = sys.executable
    preflight: dict[str, Any] = {"pytest_exit": None, "drain_exit": None, "export_exit": None}

    if not args.skip_pytest:
        for p in PYTEST_FILES:
            if not p.is_file():
                print(f"ERROR: missing pytest file: {p}", file=sys.stderr)
                return 2
        pytest_cmd = [py, "-m", "pytest", *[str(p) for p in PYTEST_FILES], "-q", "--tb=short"]
        rc = _run(pytest_cmd, cwd=root)
        preflight["pytest_exit"] = rc
        if rc != 0:
            print(f"ERROR: pytest failed exit={rc}", file=sys.stderr)
            return rc

    if not STUB.is_file():
        print(f"ERROR: missing queue stub: {STUB}", file=sys.stderr)
        return 2

    drain_cmd = [
        py,
        str(STUB),
        "drain",
        "--root",
        str(root),
        "--allow-missing-queue",
        "--max-jobs",
        "50",
    ]
    rc_d = _run(drain_cmd, cwd=root)
    preflight["drain_exit"] = rc_d
    if rc_d != 0:
        print(f"ERROR: drain failed exit={rc_d}", file=sys.stderr)
        return rc_d

    export_path = Path(args.export_temp)
    if not export_path.is_absolute():
        export_path = (root / export_path).resolve()
    export_path.parent.mkdir(parents=True, exist_ok=True)

    export_cmd = [
        py,
        str(STUB),
        "export-pending",
        "--root",
        str(root),
        "--out-json",
        str(export_path),
        "--allow-missing-queue",
        "--max-items",
        "200",
    ]
    rc_e = _run(export_cmd, cwd=root)
    preflight["export_exit"] = rc_e
    if rc_e != 0:
        print(f"ERROR: export-pending failed exit={rc_e}", file=sys.stderr)
        return rc_e

    if not export_path.is_file():
        print(f"ERROR: export output missing: {export_path}", file=sys.stderr)
        return 2

    try:
        snap = json.loads(export_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: export JSON invalid: {exc}", file=sys.stderr)
        return 2

    try:
        decision, exit_code, invalid_count = evaluate_pending_export(snap)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    items = snap.get("pending_items") if isinstance(snap.get("pending_items"), list) else []
    n_pending = len(items)

    out_path = Path(args.output)
    if not out_path.is_absolute():
        out_path = (root / out_path).resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    gate_doc: dict[str, Any] = {
        "schema": GATE_SCHEMA,
        "version": "1.0.0",
        "generated_at_utc": _utc_z(),
        "preflight": preflight,
        "export_snapshot_path": posix_rel_best(export_path, root),
        "pending_count": n_pending,
        "invalid_pending_count": invalid_count,
        "decision": decision,
        "track_wall": ["B_TRACK_RESEARCH", "ADVISORY_ONLY", "NON_GATING"],
        "promotion_tier": "S1_SHADOW",
        "fact_lock_note": (
            "S1_SHADOW: file-queue stub + drain + export contract verified in this run. "
            "No automatic lens subprocess, Track A merge, or live trading."
        ),
    }
    out_path.write_text(json.dumps(gate_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "decision": decision, "wrote": str(out_path)}, ensure_ascii=False))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
