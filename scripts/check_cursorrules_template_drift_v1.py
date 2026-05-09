from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Check .cursorrules drift against slim SSOT template.")
    p.add_argument("--workspace-root", default="C:/workspace")
    p.add_argument("--template-path", default="docs/final/artifacts/cursorrules_slim_ssot_v1.txt")
    p.add_argument("--target-path", default=".cursorrules")
    p.add_argument("--output-json", default="reports/cursorrules_drift_status_latest.json")
    return p.parse_args()


def main() -> int:
    args = parse_args()
    root = Path(args.workspace_root)
    template = root / args.template_path
    target = root / args.target_path
    out = root / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)

    if not template.exists() or not target.exists():
        payload = {
            "schema": "cursorrules_drift_status_v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ERROR",
            "reason": "missing_template_or_target",
            "template_exists": template.exists(),
            "target_exists": target.exists(),
        }
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"cursorrules_drift_status=ERROR output={out.as_posix()}")
        return 2

    t_hash = sha256(template)
    c_hash = sha256(target)
    in_sync = t_hash == c_hash
    payload = {
        "schema": "cursorrules_drift_status_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if in_sync else "DRIFT",
        "in_sync": in_sync,
        "template_path": str(template).replace("\\", "/"),
        "target_path": str(target).replace("\\", "/"),
        "template_sha256": t_hash,
        "target_sha256": c_hash,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"cursorrules_drift_status={payload['status']} output={out.as_posix()}")
    return 0 if in_sync else 1


if __name__ == "__main__":
    raise SystemExit(main())
