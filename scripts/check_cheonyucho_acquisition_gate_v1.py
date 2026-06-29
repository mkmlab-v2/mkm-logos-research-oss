#!/usr/bin/env python3
"""Gate: cheonyucho / Park 1985 acquisition — HOLD until physical_verified anchor.

Writes reports/constitution/btrack_pilot/cheonyucho_acquisition_gate_v1_latest.json

PASS (exit 0) = research_only wall correctly enforced (send_gate HOLD, canon not acquired).
FAIL (exit 1) = premature promotion or missing SSOT artifacts.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PROBE = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_probe_v1.json"
NL_PROBE = ROOT / "reports/constitution/btrack_pilot/cheonyucho_park1985_nl_probe_v1.json"
IJEOMA_SSOT = ROOT / "docs/final/artifacts/ijeoma_nl_notebook_state_ssot_v1_latest.json"
OUT = ROOT / "reports/constitution/btrack_pilot/cheonyucho_acquisition_gate_v1_latest.json"

ANCHOR_FIELDS = ("isbn", "library_call_no", "scan_sha256", "transcript_sha256", "jsg_data_id")


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _rel_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _physical_verified(probe: dict[str, Any]) -> bool:
    if probe.get("physical_verified") is True:
        return True
    last = probe.get("last_run_physical")
    if isinstance(last, dict) and last.get("physical_verified") is True:
        return True
    return False


def _has_anchor(probe: dict[str, Any]) -> bool:
    anchor = probe.get("physical_anchor") or {}
    if not isinstance(anchor, dict):
        return False
    return any(anchor.get(k) for k in ANCHOR_FIELDS)


def evaluate(
    probe: dict[str, Any],
    nl_probe: dict[str, Any] | None,
    ijeoma: dict[str, Any] | None,
) -> tuple[bool, list[str], list[dict[str, Any]]]:
    errors: list[str] = []
    checks: list[dict[str, Any]] = []

    if probe.get("schema") != "cheonyucho_acquisition_probe_v1":
        errors.append("probe: schema mismatch")
    checks.append({"kind": "probe_schema", "ok": probe.get("schema") == "cheonyucho_acquisition_probe_v1"})

    send_gate = str(probe.get("send_gate", "")).upper()
    canon = str(probe.get("hanja_canon_status", "")).lower()
    track = probe.get("track", "")
    checks.append(
        {
            "kind": "send_gate_hold",
            "send_gate": send_gate,
            "ok": send_gate == "HOLD",
        }
    )
    if send_gate != "HOLD":
        errors.append(f"send_gate must be HOLD (got {send_gate!r})")

    checks.append(
        {
            "kind": "hanja_canon_not_acquired",
            "hanja_canon_status": canon,
            "ok": canon in ("not_acquired", "partial_vol1_prefix_user_paste_2026-06-24"),
        }
    )
    if canon == "acquired":
        errors.append("hanja_canon_status must not be acquired without human gate")

    if track != "B":
        errors.append(f"track must be B (got {track!r})")

    phys = _physical_verified(probe)
    anchored = _has_anchor(probe)
    checks.append({"kind": "physical_verified", "value": phys, "anchored": anchored, "ok": not phys or anchored})
    if phys and not anchored:
        errors.append("physical_verified=true requires physical_anchor (isbn|library_call_no|scan_sha256|jsg_data_id)")

    if not phys:
        p101 = next((c for c in probe.get("checklist", []) if c.get("id") == "P1-01"), None)
        ok_p101 = bool(p101) and p101.get("status") in (
            "pending_physical_book",
            "pending",
            "nl_briefing_only",
            "nlk_no_rear_index_confirmed",
            "partial_disk_hit",
        )
        checks.append({"kind": "p1_01_pending", "status": (p101 or {}).get("status"), "ok": ok_p101})
        if not ok_p101:
            errors.append("P1-01 must remain pending until physical_verified")

    if NL_PROBE.is_file():
        nl_ok = True
        try:
            raw = _load(NL_PROBE)
            val = raw.get("value", raw)
            ans = str(val.get("answer", "")).lower()
            if "unverified" not in ans and "미확인" not in ans:
                nl_ok = False
                errors.append("park1985 NL probe answer should state UNVERIFIED/미확인")
        except (json.JSONDecodeError, OSError) as exc:
            nl_ok = False
            errors.append(f"park1985 NL probe unreadable: {exc}")
        checks.append({"kind": "park1985_nl_probe", "path": str(NL_PROBE), "ok": nl_ok})
    else:
        checks.append({"kind": "park1985_nl_probe", "ok": False, "optional": True})

    if ijeoma:
        gcy = ijeoma.get("geukchigo_cheonyu_yugo") or {}
        ssot_gate = str(ijeoma.get("send_gate_default", "")).upper()
        checks.append(
            {
                "kind": "ijeoma_ssot_send_gate",
                "send_gate_default": ssot_gate,
                "hanja_canon_status": gcy.get("hanja_canon_status"),
                "ok": ssot_gate == "HOLD",
            }
        )
        if ssot_gate != "HOLD":
            errors.append("ijeoma_nl_notebook_state send_gate_default must be HOLD")

    ok = not errors
    return ok, errors, checks


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--probe", type=Path, default=PROBE)
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()

    if not args.probe.is_file():
        print(json.dumps({"ok": False, "error": f"missing probe: {args.probe}"}))
        return 1

    probe = _load(args.probe)
    nl_probe = _load(NL_PROBE) if NL_PROBE.is_file() else None
    ijeoma = _load(IJEOMA_SSOT) if IJEOMA_SSOT.is_file() else None

    ok, errors, checks = evaluate(probe, nl_probe, ijeoma)

    doc = {
        "schema": "cheonyucho_acquisition_gate_v1",
        "version": "1.0.0",
        "generated_at_utc": _utc(),
        "ok": ok,
        "decision": "PASS" if ok else "FAIL",
        "track": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "promotion_allowed": False,
        "physical_verified": _physical_verified(probe),
        "hanja_canon_status": probe.get("hanja_canon_status"),
        "inputs": {
            "probe": _rel_path(args.probe),
            "park1985_nl_probe": _rel_path(NL_PROBE) if NL_PROBE.is_file() else None,
            "ijeoma_ssot": _rel_path(IJEOMA_SSOT) if IJEOMA_SSOT.is_file() else None,
        },
        "errors": errors,
        "checks": checks,
        "reproduce": "py scripts/check_cheonyucho_acquisition_gate_v1.py",
    }

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "decision": doc["decision"], "send_gate": "HOLD", "errors": len(errors)}))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
