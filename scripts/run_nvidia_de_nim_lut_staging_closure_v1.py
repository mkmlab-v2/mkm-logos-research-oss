#!/usr/bin/env python3
"""[HYPO] Post Phase3: LUT DE+NIM merge, salience hook, NG-40 re-eval, paste — no codec wire."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
LUT = ROOT / "experiments/nextgen_clean_slate_cpu_v1/ARCHETYPE_PRIOR_LUT_DRAFT_V1.json"
OUT = ROOT / "reports/nvidia_de_nim_lut_staging_closure_v1_latest.json"
NIM_SYN = ROOT / "reports/ng40_de_probe_nim_synthesis_v1_latest.json"
DE_PROBE = ROOT / "reports/ng40_de_logos_anchor_probe_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(script: str, extra: list[str] | None = None) -> dict[str, Any]:
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--commander-approve-lut",
        action="store_true",
        help="Also run phase5 LUT/nav approve (research; no ACTIVE apply)",
    )
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc = 0

    def _lut_merge_step() -> dict[str, Any]:
        lut_args = [
            "--de-probe-json",
            str(DE_PROBE.relative_to(ROOT)).replace("\\", "/"),
            "--patch-nav-frame",
        ]
        if NIM_SYN.is_file():
            lut_args.extend(
                [
                    "--nim-synthesis-json",
                    str(NIM_SYN.relative_to(ROOT)).replace("\\", "/"),
                ]
            )
        s = _run("scripts/build_archetype_prior_lut_draft_v1.py", lut_args)
        return {"name": "lut_de_nim_merge", **s}

    if args.commander_approve_lut:
        s2 = _run(
            "scripts/run_nextgen_phase5_commander_signoff_push_v1.py",
            ["--signoff-by", "commander", "--skip-tri-lane"],
        )
        steps.append({"name": "phase5_lut_nav_approve", **s2})

    steps.append(
        _run(
            "scripts/build_ng40_salience_hook_from_nav_frame_v1.py",
            ["--mark-wired"],
        )
    )
    steps.append(_run("scripts/run_ng40_path_b_trilane_prior_41k_eval_v1.py"))
    steps.append(
        _run(
            "scripts/run_ng40_genai_de_research_handoff_v1.py",
            ["--run-local-refresh"],
        )
    )
    s_lut = _lut_merge_step()
    steps.append(s_lut)
    if s_lut["exit_code"] != 0:
        rc = s_lut["exit_code"]
    steps.append(_run("scripts/build_nvidia_hybrid_operator_paste_pack_v1.py"))
    steps.append(_run("scripts/build_hybrid_ai_lab_status_v1.py"))
    steps.append(
        _run(
            "scripts/build_ng40_b2b_product_export_pack_v1.py",
        )
    )

    lut_doc = json.loads(LUT.read_text(encoding="utf-8-sig")) if LUT.is_file() else {}
    nim_staging = lut_doc.get("nim_anchor_staging_v1") or {}
    de_staging = lut_doc.get("de_probe_staging_v1") or {}
    closure = {
        "schema": "nvidia_de_nim_lut_staging_closure_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypo_label": "[HYPO]",
        "track_a_active_write": False,
        "lut_status": lut_doc.get("status"),
        "lut_counts": lut_doc.get("counts"),
        "nim_anchor_staging_present": bool(nim_staging),
        "verse_refs_merged_de_plus_llm": de_staging.get("verse_refs_merged_with_llm"),
        "nim_verse_refs_guess": lut_doc.get("counts", {}).get("nim_verse_refs_guess"),
        "codec_wired": False,
        "next_human_gate": "commander picks DE/NIM anchor rows in LUT; no auto codec",
        "pointers": {
            "lut": str(LUT.relative_to(ROOT)).replace("\\", "/"),
            "nim_synthesis": str(NIM_SYN.relative_to(ROOT)).replace("\\", "/"),
            "operator_paste": "reports/nvidia_hybrid_operator_paste_v1_latest.txt",
            "b2b_export": "reports/ng40_b2b_product_export_pack_v1_latest.json",
        },
        "steps": steps,
        "forbidden": ["auto_merge_into_active_codec", "--apply-active"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(closure, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    hard = any(
        s.get("exit_code", 0) != 0
        for s in steps
        if s.get("name") == "lut_de_nim_merge"
        or "path_b_trilane" in str(s.get("script", ""))
    )
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "rc": rc if rc else (1 if hard else 0),
                "lut_status": lut_doc.get("status"),
                "merged_verse_refs": lut_doc.get("counts", {}).get(
                    "verse_refs_merged_de_plus_llm"
                ),
                "nim_verse_refs_guess": lut_doc.get("counts", {}).get(
                    "nim_verse_refs_guess"
                ),
            },
            ensure_ascii=False,
        )
    )
    return rc if rc else (1 if hard else 0)


if __name__ == "__main__":
    raise SystemExit(main())
