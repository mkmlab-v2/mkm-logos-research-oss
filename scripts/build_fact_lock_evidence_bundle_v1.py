from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_FILES = [
    "reports/execution_gate_rehearsal_matrix_latest.json",
    "reports/execution_gate_audit_summary_latest.json",
    "reports/amsaeng_eosa_ops_snapshot_latest.json",
    "reports/security_integrity_status_latest.json",
    "reports/athena_ops_status_latest.json",
    "reports/cursorrules_drift_status_latest.json",
]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build fact-lock evidence bundle with file hashes.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--include-path", action="append", default=[], help="Additional relative file path to include.")
    p.add_argument("--output-json", default="reports/fact_lock_evidence_bundle_latest.json")
    p.add_argument("--append-agent-log", action="store_true")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    paths = list(dict.fromkeys(DEFAULT_FILES + args.include_path))

    files: list[dict[str, Any]] = []
    for rel in paths:
        p = root / rel
        row: dict[str, Any] = {"path": rel.replace("\\", "/"), "exists": p.exists()}
        if p.exists():
            row["sha256"] = sha256(p)
            row["size"] = p.stat().st_size
            row["last_modified_utc"] = datetime.fromtimestamp(
                p.stat().st_mtime, tz=timezone.utc
            ).isoformat()
        else:
            row["sha256"] = ""
            row["size"] = 0
            row["last_modified_utc"] = ""
        files.append(row)

    bundle = {
        "schema": "fact_lock_evidence_bundle_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "files": files,
        "missing_count": sum(1 for f in files if not f["exists"]),
    }
    out = root / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(bundle, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.append_agent_log:
        log_path = root / "reports" / "agent_decisions_log.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "timestamp": bundle["generated_at_utc"],
            "mission_id": "fact-lock-evidence-bundle",
            "stage": "report",
            "decision": "fact_lock_evidence_bundle_built",
            "evidence_path": str(out).replace("\\", "/"),
            "actor": "build_fact_lock_evidence_bundle_v1",
            "note": f"missing_count={bundle['missing_count']}",
        }
        with log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"fact_lock_evidence_bundle_written={out.as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
