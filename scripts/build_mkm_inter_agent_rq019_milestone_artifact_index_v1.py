#!/usr/bin/env python3
"""M23b: Machine-readable index of RQ-019 milestone evidence paths (from status JSON)."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

STATUS = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/mkm_inter_agent_rq019_milestone_artifact_index_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_index(*, status_path: Path = STATUS) -> dict[str, Any]:
    if not status_path.is_file():
        return {"ok": False, "error": "status_missing", "path": str(status_path)}
    status = json.loads(status_path.read_text(encoding="utf-8"))
    milestones = status.get("milestones") or {}
    rows: list[dict[str, Any]] = []
    for key, block in milestones.items():
        if not isinstance(block, dict):
            continue
        paths = list(block.get("evidence_paths") or [])
        if block.get("artifact"):
            paths.append(block["artifact"])
        if block.get("spike_path"):
            paths.append(block["spike_path"])
        rows.append(
            {
                "milestone_key": key,
                "pass": block.get("pass", block.get("status") == "pass"),
                "status": block.get("status"),
                "evidence_paths": sorted(set(paths)),
            }
        )
    all_pass = all(r.get("pass") for r in rows if r.get("milestone_key", "").startswith("m"))
    return {
        "ok": len(rows) >= 28 and all_pass,
        "schema": "mkm_inter_agent_rq019_milestone_artifact_index_v1",
        "generated_at_utc": _utc(),
        "source_status": status_path.relative_to(ROOT).as_posix(),
        "rq_019": status.get("rq_019"),
        "rq_019_language_dev_m12_m22_ready": status.get("rq_019_language_dev_m12_m22_ready"),
        "rq_019_language_dev_m12_m23_ready": status.get("rq_019_language_dev_m12_m23_ready"),
        "rq_019_language_dev_m12_m25_ready": status.get("rq_019_language_dev_m12_m25_ready"),
        "rq_019_language_dev_m12_m26_ready": status.get("rq_019_language_dev_m12_m26_ready"),
        "rq_019_language_dev_m12_m27_ready": status.get("rq_019_language_dev_m12_m27_ready"),
        "rq_019_language_dev_m12_m28_ready": status.get("rq_019_language_dev_m12_m28_ready"),
        "index_derived_from_status": True,
        "milestone_count": len(rows),
        "milestones": rows,
        "boundary_ack": "Index only; does not replace CONSTITUTION or legal sign-off.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--status", type=Path, default=STATUS)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_index(status_path=args.status)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.output)}, ensure_ascii=False))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
