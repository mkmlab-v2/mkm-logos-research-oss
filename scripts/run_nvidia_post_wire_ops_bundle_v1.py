#!/usr/bin/env python3
"""[HYPO] Post wire-confirm ops: Track C pack, B2B, BLS patrol, paste, hybrid status."""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/nvidia_post_wire_ops_bundle_v1_latest.json"
WIRE = ROOT / "reports/nvidia_lut_codec_staging_wire_confirm_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run_py(script: str, extra: list[str] | None = None) -> dict[str, Any]:
    cmd = [sys.executable, str(ROOT / script), *(extra or [])]
    cp = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    tail = (cp.stdout or "").strip().splitlines()
    parsed = None
    if tail:
        try:
            parsed = json.loads(tail[-1])
        except json.JSONDecodeError:
            parsed = {"raw_tail": tail[-1][:400]}
    return {"script": script, "args": extra or [], "exit_code": int(cp.returncode), "parsed": parsed}


def _run_ps1(rel: str, extra: list[str] | None = None) -> dict[str, Any]:
    ps = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(ROOT / rel),
        *(extra or []),
    ]
    cp = subprocess.run(ps, cwd=str(ROOT), capture_output=True, text=True)
    return {
        "script": rel,
        "args": extra or [],
        "exit_code": int(cp.returncode),
        "parsed": {"stdout_tail": (cp.stdout or "")[-500:]},
    }


def main() -> int:
    if not WIRE.is_file():
        print(json.dumps({"error": "run_lut_codec_staging_wire_pipeline_first"}))
        return 2

    steps: list[dict[str, Any]] = []
    rc = 0

    steps.append(_run_py("scripts/build_nvidia_lut_codec_staging_review_v1.py"))
    steps.append(_run_py("scripts/run_ng40_b2b_product_export_chain_v1.py", ["--skip-refresh"]))
    s_tc = _run_ps1("scripts/Invoke-TrackCB2bMeetingPack_v1.ps1")
    steps.append({"name": "track_c_b2b_meeting_pack", **s_tc})
    if s_tc["exit_code"] != 0:
        rc = s_tc["exit_code"]

    s_bls = _run_py("scripts/probe_bls_unemployment_may2026_v1.py")
    steps.append({"name": "bls_probe", **s_bls})
    bls_resolved = False
    probe = ROOT / "reports/bls_unemployment_probe_v1_latest.json"
    if probe.is_file():
        doc = json.loads(probe.read_text(encoding="utf-8-sig"))
        if doc.get("may_2026_release_ready") and doc.get("suggested_outcome") is not None:
            s_res = _run_ps1(
                "scripts/Invoke-GeneralProphecyBlsUnrateResolve_v1.ps1",
                [
                    "-Outcome",
                    "true" if doc.get("suggested_outcome") else "false",
                ],
            )
            steps.append({"name": "bls_resolve", **s_res})
            bls_resolved = s_res["exit_code"] == 0

    showroom_smoke: dict[str, Any] = {"ok": None, "pointer": None}
    sp = ROOT / "reports/showroom_trust_viz_public_chain_smoke_latest.json"
    if sp.is_file():
        showroom_smoke = {
            "ok": json.loads(sp.read_text(encoding="utf-8-sig")).get("ok"),
            "pointer": str(sp.relative_to(ROOT)).replace("\\", "/"),
        }
    steps.append({"name": "showroom_dual_host_smoke", **showroom_smoke})

    steps.append(_run_py("scripts/build_nvidia_hybrid_operator_paste_pack_v1.py"))
    steps.append(_run_py("scripts/build_hybrid_ai_lab_status_v1.py"))
    steps.append(_run_py("scripts/check_track_c_b2b_meeting_pack_readiness_v1.py"))
    s_disc = _run_py("scripts/check_track_c_b2b_disclaimer_integrity_v1.py")
    steps.append({"name": "track_c_b2b_disclaimer_integrity", **s_disc})

    readiness = {}
    rp = ROOT / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
    if rp.is_file():
        readiness = json.loads(rp.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "nvidia_post_wire_ops_bundle_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "wire_confirm_pointer": str(WIRE.relative_to(ROOT)).replace("\\", "/"),
        "bls_resolved": bls_resolved,
        "track_c_readiness": {
            "ready_for_internal_meeting": readiness.get("ready_for_internal_meeting"),
            "ready_for_external_send": readiness.get("ready_for_external_send"),
        },
        "showroom_dual_host_smoke_ok": showroom_smoke.get("ok"),
        "disclaimer_integrity_ok": (
            json.loads(
                (ROOT / "reports/track_c_b2b_disclaimer_integrity_v1_latest.json").read_text(
                    encoding="utf-8-sig"
                )
            ).get("integrity_ok")
            if (ROOT / "reports/track_c_b2b_disclaimer_integrity_v1_latest.json").is_file()
            else None
        ),
        "steps": steps,
    }
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"wrote": str(OUT), "rc": rc, **doc["track_c_readiness"]}, ensure_ascii=False))
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
