#!/usr/bin/env python3
"""Track L L9–L12 readiness: PUBLIC_FACING lint + external send sign-off template + gate chain."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
L68_SCRIPT = ROOT / "scripts/run_logos_track_l_l6_l8_readiness_v1.py"
PUBLIC_LINT = ROOT / "scripts/check_logos_track_l_public_facing_readiness_v1.py"
DEFAULT_OUT = ROOT / "docs/final/artifacts/logos_track_l_l9_l12_readiness_v1_latest.json"

SIGNOFF_TEMPLATE = ROOT / "docs/final/artifacts/logos_track_l_external_send_signoff_v1_latest.json"
PUBLIC_LINT_OUT = ROOT / "reports/logos_track_l_public_facing_readiness_v1_latest.json"
PUBLIC_CHECKLIST = ROOT / "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md"
EVIDENCE_PACK = ROOT / "docs/final/artifacts/logos_graphrag_bridge_evidence_pack_v1_latest.json"

READINESS_CHAIN = [
    ("L0", ROOT / "docs/final/artifacts/logos_track_l_l0_readiness_v1_latest.json", "l0_ok"),
    ("L1", ROOT / "docs/final/artifacts/logos_track_l_l1_readiness_v1_latest.json", "l1_ok"),
    ("L2", ROOT / "docs/final/artifacts/logos_track_l_l2_readiness_v1_latest.json", "l2_ok"),
    ("L3", ROOT / "docs/final/artifacts/logos_track_l_l3_readiness_v1_latest.json", "l3_ok"),
    ("L4_L5", ROOT / "docs/final/artifacts/logos_track_l_l4_l5_readiness_v1_latest.json", "l4_l5_ok"),
    ("L6_L8", ROOT / "docs/final/artifacts/logos_track_l_l6_l8_readiness_v1_latest.json", "l6_l8_ok"),
]


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve())).replace("\\", "/")
    except ValueError:
        return str(path.resolve().as_posix())


def _run_py(args: list[str], *, timeout: int = 420) -> tuple[int, str]:
    proc = subprocess.run(
        [sys.executable, *args],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=timeout,
    )
    tail = (proc.stdout or proc.stderr or "").strip()
    return proc.returncode, tail[-1200:] if len(tail) > 1200 else tail


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return obj if isinstance(obj, dict) else {}


def build_report(*, skip_l68: bool) -> dict[str, Any]:
    l68: dict[str, Any]
    if skip_l68:
        l68_doc = _read_json(ROOT / "docs/final/artifacts/logos_track_l_l6_l8_readiness_v1_latest.json")
        l68 = {"skipped": True, "l6_l8_ok": bool(l68_doc.get("l6_l8_ok"))}
    else:
        rc, tail = _run_py([str(L68_SCRIPT), "--skip-l45", "--rebuild-packet"], timeout=480)
        l68_doc = _read_json(ROOT / "docs/final/artifacts/logos_track_l_l6_l8_readiness_v1_latest.json")
        l68 = {"exit_code": rc, "l6_l8_ok": bool(l68_doc.get("l6_l8_ok")) and rc == 0, "tail": tail}

    rc_lint, tail_lint = _run_py([str(PUBLIC_LINT)], timeout=120)
    lint_doc = _read_json(PUBLIC_LINT_OUT)
    lint_check = {
        "exit_code": rc_lint,
        "ok": rc_lint == 0 and bool(lint_doc.get("ready_for_internal_track_c_draft")),
        "ready_for_external_send": lint_doc.get("ready_for_external_send"),
        "artifact": _rel(PUBLIC_LINT_OUT),
        "tail": tail_lint,
    }

    chain_rows: list[dict[str, Any]] = []
    chain_ok = True
    for label, path, ok_field in READINESS_CHAIN:
        doc = _read_json(path)
        ok = bool(doc.get(ok_field)) if ok_field in doc else path.is_file()
        chain_rows.append({"gate": label, "path": _rel(path), "ok": ok, "ok_field": ok_field})
        chain_ok = chain_ok and ok

    signoff_doc = _read_json(SIGNOFF_TEMPLATE)
    evidence_doc = _read_json(EVIDENCE_PACK)
    signoff_check = {
        "template_exists": SIGNOFF_TEMPLATE.is_file(),
        "schema_ok": signoff_doc.get("schema") == "logos_track_l_external_send_signoff_v1",
        "ready_for_external_send_false": signoff_doc.get("ready_for_external_send") is False,
        "legal_present": (signoff_doc.get("legal_counsel_signoff") or {}).get("present") is True,
        "commander_present_in_template": (signoff_doc.get("commander_signoff") or {}).get("present") is True,
    }
    signoff_ok = bool(
        signoff_check["template_exists"]
        and signoff_check["schema_ok"]
        and signoff_check["ready_for_external_send_false"]
    )

    l9_l12_ok = bool(
        (l68.get("skipped") or l68.get("l6_l8_ok"))
        and chain_ok
        and lint_check["ok"]
        and signoff_ok
        and signoff_check["ready_for_external_send_false"]
        and evidence_doc.get("ready_for_external_send") is False
        and PUBLIC_CHECKLIST.is_file()
    )

    return {
        "schema": "logos_track_l_l9_l12_readiness_v1",
        "generated_at_utc": _utc_now(),
        "ready_for_external_send": False,
        "ready_for_internal_track_c_draft": l9_l12_ok,
        "track_wall": {
            "logos_non_gating": True,
            "a_track_auto_promote": False,
            "live_trading_trigger": False,
            "legal_counsel_required_for_external_send": True,
        },
        "l9_l12_ok": l9_l12_ok,
        "checks": {
            "l6_l8_prerequisite": l68,
            "readiness_chain_l0_l6": chain_rows,
            "public_facing_lint": lint_check,
            "external_send_signoff_template": signoff_check,
            "public_facing_checklist": {"exists": PUBLIC_CHECKLIST.is_file(), "path": _rel(PUBLIC_CHECKLIST)},
            "evidence_pack_external_send_false": evidence_doc.get("ready_for_external_send") is False,
        },
        "signoff_template_path": _rel(SIGNOFF_TEMPLATE),
        "pointer": "docs/final/MKM_PROMOTION_GATE_CHECKLIST_L0_L12_V1.md §L9–L12",
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Track L L9–L12 public send readiness")
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--skip-l68", action="store_true")
    args = ap.parse_args(argv)

    doc = build_report(skip_l68=args.skip_l68)
    out = args.output_json if args.output_json.is_absolute() else ROOT / args.output_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": doc["l9_l12_ok"],
                "ready_for_external_send": doc["ready_for_external_send"],
                "wrote": str(out),
            },
            ensure_ascii=False,
        )
    )
    return 0 if doc["l9_l12_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
