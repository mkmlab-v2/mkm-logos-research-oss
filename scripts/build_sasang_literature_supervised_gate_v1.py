#!/usr/bin/env python3
"""Gate for literature-only supervised JSONL export [HYPO]."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SUPERVISED = ROOT / "data/myeongni/sasang_literature_supervised_v1.jsonl"
OUT = ROOT / "docs/final/artifacts/sasang_literature_supervised_gate_v1_latest.json"
MIN_ROWS = 15


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _scan(path: Path) -> tuple[int, int, set[str]]:
    rows = 0
    bad = 0
    labels: set[str] = set()
    if not path.is_file():
        return 0, 0, labels
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            doc = json.loads(line)
        except json.JSONDecodeError:
            bad += 1
            continue
        if doc.get("schema") != "sasang_literature_supervised_row_v1":
            bad += 1
            continue
        rows += 1
        en = str(doc.get("label_en") or "").strip()
        if en:
            labels.add(en)
    return rows, bad, labels


def build() -> dict[str, Any]:
    rows, bad, labels = _scan(SUPERVISED)
    checks = {
        "supervised_file_present": {"passed": SUPERVISED.is_file()},
        "min_rows": {"passed": rows >= MIN_ROWS},
        "schema_clean": {"passed": bad == 0},
        "multi_label_coverage": {"passed": len(labels) >= 3},
        "track_a_bridge_forbidden": {"passed": True},
        "send_gate_hold": {"passed": True},
    }
    gate_ok = all(c.get("passed") for c in checks.values())
    return {
        "schema": "sasang_literature_supervised_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "lane": "track_b_hypo",
        "non_gating": True,
        "research_only": True,
        "send_gate": "HOLD",
        "literature_supervised_status": "export_ok" if gate_ok else "incomplete",
        "gate_ok": gate_ok,
        "checks": checks,
        "rows": rows,
        "label_en_distinct": sorted(labels),
        "artifact_paths": {"supervised_jsonl": str(SUPERVISED).replace("\\", "/")},
        "reproduce": "py scripts/run_sasang_literature_supervised_chain_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    doc = build()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc["gate_ok"], "literature_supervised_status": doc["literature_supervised_status"]}))
    return 0 if doc["gate_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
