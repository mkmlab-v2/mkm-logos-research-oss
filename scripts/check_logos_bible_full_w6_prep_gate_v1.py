#!/usr/bin/env python3
"""W6 OSS release prep — solo OSS policy aligned (no counsel/metering default gate).

  py scripts/check_logos_bible_full_w6_prep_gate_v1.py
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
OUT = ROOT / "reports/logos_bible_full_w6_prep_gate_v1_latest.json"
SOLO_POLICY = ROOT / "docs/final/artifacts/mkm_solo_oss_release_policy_v1_latest.json"

STUDIO_COPY_PATHS = [
    ROOT / "projects/no1kmedi/marketing-site/logos-research-copy.json",
    ROOT / "projects/no1kmedi/marketing-site/logos-research-docs-copy.json",
    ROOT / "projects/no1kmedi/src/content/logosResearchCopy.ts",
]

FORBIDDEN_PUBLIC = ("지휘관", "commander_only", "MKM_COMMANDER")


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str]) -> tuple[int, dict[str, Any]]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, encoding="utf-8")
    tail = (proc.stdout or proc.stderr or "").strip()
    try:
        doc = json.loads(tail.split("\n")[-1] if tail else "{}")
    except json.JSONDecodeError:
        doc = {"raw": tail[-500:]}
    return proc.returncode, doc


def _scan_studio_copy() -> dict[str, Any]:
    hits: list[dict[str, str]] = []
    for path in STUDIO_COPY_PATHS:
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in FORBIDDEN_PUBLIC:
            if token in text:
                hits.append({"path": str(path.relative_to(ROOT)), "token": token})
    return {"ok": not hits, "forbidden_hits": hits}


def _solo_policy() -> dict[str, Any]:
    if not SOLO_POLICY.is_file():
        return {"ok": False, "error": "missing_solo_policy"}
    doc = json.loads(SOLO_POLICY.read_text(encoding="utf-8-sig"))
    scope = doc.get("send_gate_scope") or {}
    return {
        "ok": scope.get("oss_github_release") == "OPEN",
        "send_gate_scope": scope,
        "deprecated_counsel_default": (doc.get("deprecated_paths") or {})
        .get("legal_counsel_signoff_bundle", {})
        .get("do_not_suggest_in_chat"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    args = ap.parse_args()
    failures: list[str] = []

    solo = _solo_policy()
    if not solo.get("ok"):
        failures.append("solo_oss_policy")

    gov_exit, gov_doc = _run([PY, "scripts/check_logos_bible_full_governance_hold_gate_v1.py"])
    if gov_exit != 0 or gov_doc.get("ok") is not True:
        failures.append("governance_hold_gate")

    pf_exit, pf_doc = _run([PY, "scripts/check_logos_track_l_public_facing_readiness_v1.py"])
    if pf_exit != 0:
        failures.append("public_facing_readiness")

    oss_exit, oss_doc = _run([PY, "scripts/run_logos_oss_premarket_smoke_v1.py"])
    if oss_exit != 0 or oss_doc.get("ok") is not True:
        failures.append("oss_premarket_smoke")

    export_exit, export_doc = _run([PY, "scripts/build_logos_oss_public_export_bundle_v1.py", "--verify-only"])
    if export_exit != 0 or export_doc.get("ok") is not True:
        failures.append("oss_export_manifest_verify")

    copy_scan = _scan_studio_copy()
    if not copy_scan["ok"]:
        failures.append("studio_copy_forbidden_token")

    audit_path = ROOT / "docs/final/artifacts/logos_bible_full_coverage_audit_v1_latest.json"
    layers_ok = False
    if audit_path.is_file():
        audit = json.loads(audit_path.read_text(encoding="utf-8-sig"))
        layers = {str(ly["id"]): float(ly.get("canon_coverage_pct") or 0) for ly in audit.get("layers") or []}
        layers_ok = (
            layers.get("studio_citation_shard_krv", 0) >= 99.9
            and layers.get("bible_meaning_graph_nodes", 0) >= 99.9
            and layers.get("studio_graph_slice", 0) >= 99.9
        )
        if not layers_ok:
            failures.append("audit_layers_below_w5")

    doc = {
        "schema": "logos_bible_full_w6_prep_gate_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "release_gate": "OPEN_SOURCE_PREP",
        "send_gate_scope": solo.get("send_gate_scope") or {
            "oss_github_release": "OPEN",
            "grants_customer_contracts": "HOLD",
            "track_a_live_trading": "LOCKED",
        },
        "track_a_auto_promote": False,
        "ok": not failures,
        "failures": failures,
        "solo_oss_policy": solo,
        "governance_hold": gov_doc,
        "public_facing": pf_doc,
        "oss_premarket_smoke": oss_doc,
        "oss_export_verify": export_doc,
        "studio_copy_scan": copy_scan,
        "w5_layers_ok": layers_ok,
        "human_gate_remaining": [
            "Push-GitHub-Explicit.ps1 -Acknowledge (public push only)",
            "Optional: py scripts/build_logos_oss_public_export_bundle_v1.py --materialize",
        ],
        "explicitly_not_default_gates": [
            "legal counsel L12 sign-off",
            "LOGOS_RESEARCH_PRO_API_KEYS metering",
        ],
        "reproduce": "py scripts/check_logos_bible_full_w6_prep_gate_v1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"ok": doc["ok"], "release_gate": doc["release_gate"], "failures": failures, "out": str(OUT)},
            ensure_ascii=False,
        )
    )
    return 0 if doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
