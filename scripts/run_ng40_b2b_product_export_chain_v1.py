#!/usr/bin/env python3
"""[HYPO] Refresh Path A product artifacts + B2B export pack + promotion sign-off."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "reports/ng40_b2b_product_export_chain_v1_latest.json"
PROBE = ROOT / "reports/bls_unemployment_probe_v1_latest.json"


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
    ap.add_argument("--skip-refresh", action="store_true", help="Only build pack from disk")
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    rc = 0

    if not args.skip_refresh:
        s = _run(
            "scripts/run_ng40_path_a_product_signoff_chain_v1.py",
            ["--skip-auto-ops"],
        )
        steps.append({"name": "path_a_product_refresh", **s})
        if s["exit_code"] != 0:
            rc = s["exit_code"]

    s_pack = _run("scripts/build_ng40_b2b_product_export_pack_v1.py")
    steps.append({"name": "b2b_export_pack", **s_pack})
    if s_pack["exit_code"] != 0 and rc == 0:
        rc = s_pack["exit_code"]

    s_promo = _run(
        "scripts/build_btrack_nextgen_promotion_candidate_packet_v1.py",
        [
            "--path-b-knee-research-signoff",
            "--path-a-product-research-signoff",
            "--reviewer",
            "commander",
            "--note",
            "B2B product export pack + research lanes 2026-06-04",
        ],
    )
    steps.append({"name": "promotion_packet", **s_promo})

    s_bls = _run("scripts/probe_bls_unemployment_may2026_v1.py")
    steps.append({"name": "bls_probe", **s_bls})

    pack = {}
    pack_path = ROOT / "reports/ng40_b2b_product_export_pack_v1_latest.json"
    if pack_path.is_file():
        pack = json.loads(pack_path.read_text(encoding="utf-8-sig"))

    doc = {
        "schema": "ng40_b2b_product_export_chain_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "track_a_active_write": False,
        "steps": steps,
        "product_ready": pack.get("product_lane", {}).get("product_ready"),
        "export_pack_pointer": "reports/ng40_b2b_product_export_pack_v1_latest.json",
        "paste_pointer": "reports/ng40_b2b_product_export_paste_v1_latest.txt",
        "export_prep_ready": (s_promo.get("parsed") or {}).get("export_prep_ready"),
        "forbidden": ["--apply-active", "latent_in_b2b_headline"],
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "wrote": str(OUT),
                "rc": rc,
                "product_ready": doc["product_ready"],
                "export_prep_ready": doc["export_prep_ready"],
            },
            ensure_ascii=False,
        )
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
