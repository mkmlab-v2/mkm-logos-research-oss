#!/usr/bin/env python3
"""MS RQ-019 show mission — aggregate gate status (read-only artifact scan)."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_OUT = ROOT / "reports/ms_rq019_auto_status_latest.json"

ENCODING = ROOT / "docs/final/artifacts/mkm_inter_agent_encoding_status_latest.json"
FINOPS_OFFICIAL = ROOT / "docs/final/artifacts/finops_wire_domain_v1_closeout_official_v1_latest.json"
FINOPS_EVAL = ROOT / "reports/finops_wire_domain_v1_eval_latest.json"
PUBLIC_GATE_JSON = ROOT / "reports/ms_rq019_public_facing_gate_latest.json"
PUBLIC_GATE_MD = ROOT / "reports/ms_rq019_public_facing_gate_latest.md"
PASTE_ORDER = ROOT / "reports/ms_rq019_paste_ready/00_paste_order.txt"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _public_facing_internal_pass() -> bool:
    if PUBLIC_GATE_JSON.is_file():
        doc = _read(PUBLIC_GATE_JSON)
        return doc.get("ok") is True or doc.get("internal_pass") is True
    if PUBLIC_GATE_MD.is_file():
        text = PUBLIC_GATE_MD.read_text(encoding="utf-8")
        return "PASS (internal meeting)" in text
    return False


def _run_weekly_smoke() -> dict[str, Any]:
    ps1 = ROOT / "scripts/Run-MkmInterAgentRq019WeeklySmoke_v1.ps1"
    if not ps1.is_file():
        return {"ok": False, "error": "smoke_script_missing"}
    cp = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return {"ok": cp.returncode == 0, "exit_code": cp.returncode, "tail": (cp.stdout or cp.stderr or "")[-400:]}


def build_status(*, run_smoke: bool = False) -> dict[str, Any]:
    enc = _read(ENCODING)
    finops = _read(FINOPS_OFFICIAL)
    finops_ev = _read(FINOPS_EVAL)
    smoke = _run_weekly_smoke() if run_smoke else {"ok": None, "skipped": True}
    pub_ok = _public_facing_internal_pass()

    finops_l1_official = (
        finops.get("ok") is True and finops.get("approval_status") == "APPROVED_COMMANDER"
    )
    finops_gates_ok = finops_ev.get("ok") is True

    gates = {
        "weekly_smoke_exit_0": smoke.get("ok") if run_smoke else enc.get("rq_019_milestones_core_ready"),
        "rq_019_milestones_core_ready": enc.get("rq_019_milestones_core_ready") is True,
        "finops_domain_v1_eval_ok": finops_gates_ok,
        "finops_l1_official_closeout": finops_l1_official,
        "public_facing_internal_pass": pub_ok,
        "paste_order_exists": PASTE_ORDER.is_file(),
    }

    human = [
        "ms_form_paste: K1-K3 (paste_ready/*.txt or body MD)",
        "commander_verbal: 시연 리허설 OK (optional)",
        "legal_send: after counsel",
        "l2_pilot_corpus: optional customer logs",
    ]
    if finops_l1_official:
        human = [h for h in human if not h.startswith("finops_l1")]

    return {
        "ok": all(v is True for k, v in gates.items() if v is not None),
        "schema": "ms_rq019_auto_status_v1",
        "generated_at_utc": _utc(),
        "mission": "M-MS-RQ019-SHOW",
        "core_frozen": True,
        "rq_019": enc.get("rq_019") or "CLOSED",
        "finops_domain": {
            "l1_official": finops_l1_official,
            "official_pointer": FINOPS_OFFICIAL.relative_to(ROOT).as_posix() if finops_l1_official else None,
            "approved_at_utc": finops.get("approved_at_utc"),
            "lane": finops.get("lane"),
        },
        "gates": gates,
        "human_remainder": human,
        "pointers": {
            "pack_index": "reports/ms_rq019_submission_pack_index_latest.md",
            "evidence_index": "reports/ms_rq019_evidence_index_latest.md",
            "paste_order": PASTE_ORDER.relative_to(ROOT).as_posix() if PASTE_ORDER.is_file() else None,
            "finops_official": FINOPS_OFFICIAL.relative_to(ROOT).as_posix(),
            "finops_scope": "reports/finops_wire_domain_scope_v1_latest.md",
        },
        "demo_urls": {
            "local_wire_v3": "file:///C:/workspace/reports/demo/ms_rq019_wire_showroom_v3.html",
            "cloud_wire_v3": "https://jemaai.cloud/public_showroom_mkm_inter_agent_wire_v3.html",
            "cloud_oracle_v3": "https://jemaai.cloud/public_showroom_logos_oracle_v3.html",
            "cloud_oracle_v4_visual_path": "https://jemaai.cloud/public_showroom_logos_oracle_v4.html",
            "cloud_oracle_v5_enterprise": "https://jemaai.cloud/public_showroom_logos_oracle_v5.html",
        },
        "showroom_smoke": "reports/showroom_trust_viz_public_chain_smoke_latest.json",
        "boundary_ack": "Auto status is internal gate scan only; not MS submission approval or legal send.",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-smoke", action="store_true", help="Run weekly smoke (slower)")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()
    doc = build_status(run_smoke=args.run_smoke)
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": doc.get("ok"), "output": str(args.out_json.resolve())}))
    return 0 if doc.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
