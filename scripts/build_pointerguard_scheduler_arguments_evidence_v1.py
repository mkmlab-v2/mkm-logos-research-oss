#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ART = ROOT / "docs" / "final" / "artifacts"
OUT_DEFAULT = ART / "pointerguard_scheduler_arguments_evidence_latest.json"
TASK_NAME_DEFAULT = "MKM_PointerGuard_ControlChain_Daily"


def _now_utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _extract_between(text: str, start: str, end: str) -> str:
    s = text.find(start)
    if s < 0:
        return ""
    s += len(start)
    e = text.find(end, s)
    if e < 0:
        return ""
    return text[s:e]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--task-name", type=str, default=TASK_NAME_DEFAULT)
    ap.add_argument("--out", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    cp = subprocess.run(
        ["schtasks", "/Query", "/TN", args.task_name, "/XML"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )
    if cp.returncode != 0:
        raise SystemExit(f"schtasks query failed: {cp.stderr.strip()}")
    xml_text = cp.stdout
    command = _extract_between(xml_text, "<Command>", "</Command>").strip()
    arguments = _extract_between(xml_text, "<Arguments>", "</Arguments>").strip()
    contains_flag = '-WeeklyP0DrillDay "' in arguments

    out_doc = {
        "schema": "pointerguard_scheduler_arguments_evidence_v1",
        "generated_at_utc": _now_utc(),
        "source": "schtasks_query_xml",
        "task_name": args.task_name,
        "verified": bool(command and arguments),
        "command": command,
        "arguments": arguments,
        "contains_weekly_p0_drill_day_flag": contains_flag,
    }
    out_path = args.out if args.out.is_absolute() else ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "out": str(out_path), "contains_weekly_p0_drill_day_flag": contains_flag}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
