#!/usr/bin/env python3
"""BigSet Tier-0 ingest spike chain — bridge → timeline_repair → citation_lock → timeline_order → atypical_signal → conflict_surface → digestion.

B-track · tier_0 default (dry-run) · completion JSON.

Reproducible:
  py scripts/run_bigset_ingest_spike_chain_v1.py
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
PY = sys.executable
BRIDGE = ROOT / "scripts/bigset_agent_bridge_v1.py"
CITATION_LOCK = ROOT / "scripts/check_bigset_tier0_citation_lock_v1.py"
TIMELINE_REPAIR = ROOT / "scripts/repair_bigset_tier0_timeline_order_v1.py"
TIMELINE_ORDER = ROOT / "scripts/check_bigset_tier0_timeline_order_v1.py"
ATYPICAL_SIGNAL = ROOT / "scripts/detect_bigset_tier0_atypical_signal_v1.py"
REVIEW_QUEUE = ROOT / "scripts/bigset_tier0_atypical_human_review_queue_stub_v1.py"
CONFLICT_SURFACE = ROOT / "scripts/build_bigset_conflict_surface_v1.py"
STUDIO_SIDECAR = ROOT / "scripts/build_bigset_studio_conflict_sidecar_v1.py"
DIGESTION = ROOT / "scripts/run_mkm_digestion_engine_chain_v1.py"
CHECK_AGPL = ROOT / "scripts/check_bigset_agpl_isolation_wall_v1.py"
CONFIGURE_CREDS = ROOT / "scripts/configure_bigset_local_credentials_v1.py"
CONFIGURE_AZURE_KEYCHAIN = ROOT / "scripts/configure_bigset_azure_keychain_v1.py"
FREE_TIER_APPLY = ROOT / "scripts/apply_bigset_free_tier_profile_v1.py"
OUT_REPORT = ROOT / "reports/bigset_ingest_spike_chain_v1_latest.json"
OUT_ARTIFACT = ROOT / "docs/final/artifacts/bigset_ingest_spike_chain_v1_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _run(cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    return {
        "cmd": " ".join(cmd),
        "exit_code": proc.returncode,
        "ok": proc.returncode == 0,
        "stdout_tail": (proc.stdout or "").strip()[-400:],
        "stderr_tail": (proc.stderr or "").strip()[-400:],
    }


def _count_live_rows(csv_path: Path) -> int:
    if not csv_path.is_file():
        return 0
    import csv

    hosts = ("example.org", "example.com")
    count = 0
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        for row in csv.DictReader(f):
            url = str(row.get("source_url") or "").lower()
            if not url or any(h in url for h in hosts):
                continue
            count += 1
    return count


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true", help="pass --live to bridge (BYOK)")
    ap.add_argument(
        "--auto-setup",
        action="store_true",
        help="before --live: py scripts/configure_bigset_local_credentials_v1.py",
    )
    ap.add_argument("--skip-digestion", action="store_true")
    ap.add_argument("--skip-bridge", action="store_true", help="reuse existing tier0 csv (post-live reprocess)")
    ap.add_argument(
        "--force-bridge",
        action="store_true",
        help="run bridge dry-run/live even when live rows exist (overwrites CSV)",
    )
    ap.add_argument("--skip-timeline-repair", action="store_true")
    ap.add_argument("--skip-atypical-signal", action="store_true")
    ap.add_argument("--skip-human-review-queue", action="store_true")
    ap.add_argument("--topic-slug", default="benei_haelohim_cross_refs")
    ap.add_argument("--free-tier", action="store_true", help="apply OpenRouter :free profile (restart bigset first)")
    ap.add_argument("--free-tier-mode", choices=["openrouter_free", "ollama", "azure"], default=None)
    args = ap.parse_args()

    slug = args.topic_slug
    csv_path = ROOT / "docs/research/raw" / f"bigset_{slug}_tier0_v1.csv"
    md_path = ROOT / "docs/research/raw" / f"bigset_{slug}_tier0_v1.md"

    live_rows = _count_live_rows(csv_path)
    skip_bridge = args.skip_bridge
    if not args.force_bridge and not skip_bridge and live_rows >= 5:
        skip_bridge = True

    nodes: list[dict[str, Any]] = []
    ok_all = True
    citation_gate_ok = False
    timeline_gate_ok = False
    promotion_mode = "shadow_only"
    free_profile: dict[str, Any] | None = None

    if args.free_tier:
        ft_cmd = [PY, str(FREE_TIER_APPLY)]
        if args.free_tier_mode == "ollama":
            ft_cmd.extend(["--mode", "ollama"])
        elif args.free_tier_mode == "azure":
            ft_cmd.extend(["--mode", "azure"])
        nodes.append(_run(ft_cmd))
        if not nodes[-1]["ok"]:
            ok_all = False
        art = ROOT / "docs/final/artifacts/bigset_free_tier_profile_v1_latest.json"
        if art.is_file():
            free_profile = json.loads(art.read_text(encoding="utf-8")).get("applied")
        nodes.append(
            {
                "step": "bigset_restart_note",
                "ok": True,
                "note": "bigset backend must be started with free-tier env (Invoke-BigSetFreeTierStart_v1.ps1)",
            }
        )

    nodes.append(_run([PY, str(CHECK_AGPL)]))
    if not nodes[-1]["ok"]:
        ok_all = False

    if args.live and args.auto_setup:
        if args.free_tier_mode == "azure":
            cred_cmd = [PY, str(CONFIGURE_AZURE_KEYCHAIN)]
        else:
            cred_cmd = [PY, str(CONFIGURE_CREDS)]
        nodes.append(_run(cred_cmd))
        if not nodes[-1]["ok"]:
            ok_all = False

    if not skip_bridge:
        bridge_cmd = [PY, str(BRIDGE), "--topic-slug", slug]
        if args.live:
            bridge_cmd.append("--live")
        else:
            bridge_cmd.append("--dry-run")
        nodes.append(_run(bridge_cmd))
        if not nodes[-1]["ok"]:
            ok_all = False
    else:
        note = "skip_bridge_reuse_existing_csv"
        if live_rows >= 5 and not args.skip_bridge:
            note = "auto_preserve_live_csv"
        nodes.append(
            {
                "step": "bridge",
                "skipped": True,
                "ok": csv_path.is_file(),
                "note": note,
                "live_rows": live_rows,
                "csv": str(csv_path),
            }
        )
        if not csv_path.is_file():
            ok_all = False

    if ok_all and csv_path.is_file():
        active_csv = csv_path
        if not args.skip_timeline_repair:
            repair_out = ROOT / "docs/final/artifacts/bigset_tier0_timeline_repair_v1_latest.csv"
            nodes.append(
                _run([PY, str(TIMELINE_REPAIR), "--csv", str(csv_path), "--out-csv", str(repair_out)])
            )
            if not nodes[-1]["ok"]:
                ok_all = False
            elif repair_out.is_file():
                active_csv = repair_out

        nodes.append(_run([PY, str(CITATION_LOCK), "--csv", str(active_csv), "--offline"]))
        if not nodes[-1]["ok"]:
            ok_all = False
        else:
            lock_art = ROOT / "docs/final/artifacts/bigset_tier0_citation_lock_v1_latest.json"
            if lock_art.is_file():
                lock_doc = json.loads(lock_art.read_text(encoding="utf-8"))
                citation_gate_ok = bool(lock_doc.get("gate_ok"))
                promotion_mode = str(lock_doc.get("promotion_mode") or "shadow_only")

        nodes.append(_run([PY, str(TIMELINE_ORDER), "--csv", str(active_csv)]))
        if not nodes[-1]["ok"]:
            ok_all = False
        else:
            tl_art = ROOT / "docs/final/artifacts/bigset_tier0_timeline_order_v1_latest.json"
            if tl_art.is_file():
                tl_doc = json.loads(tl_art.read_text(encoding="utf-8"))
                timeline_gate_ok = bool(tl_doc.get("gate_ok"))

        if not args.skip_atypical_signal:
            nodes.append(
                _run(
                    [
                        PY,
                        str(ATYPICAL_SIGNAL),
                        "--csv",
                        str(active_csv),
                    ]
                )
            )
            # observability only — non-fatal

            if not args.skip_human_review_queue:
                atyp_art = ROOT / "docs/final/artifacts/bigset_tier0_atypical_signal_v1_latest.json"
                if atyp_art.is_file():
                    nodes.append(
                        _run(
                            [
                                PY,
                                str(REVIEW_QUEUE),
                                "enqueue-from-signals",
                                "--signals-json",
                                str(atyp_art),
                                "--source-csv",
                                str(active_csv),
                            ]
                        )
                    )
                    nodes.append(
                        _run(
                            [
                                PY,
                                str(REVIEW_QUEUE),
                                "export-pending",
                            ]
                        )
                    )
                    # queue stub — non-fatal

        nodes.append(_run([PY, str(CONFLICT_SURFACE), "--csv", str(active_csv)]))
        if not nodes[-1]["ok"]:
            ok_all = False
        else:
            nodes.append(_run([PY, str(STUDIO_SIDECAR)]))
            if not nodes[-1]["ok"]:
                ok_all = False
    else:
        nodes.append({"step": "timeline_repair", "skipped": True, "ok": False})
        nodes.append({"step": "citation_lock", "skipped": True, "ok": False})
        nodes.append({"step": "timeline_order", "skipped": True, "ok": False})
        nodes.append({"step": "conflict_surface", "skipped": True, "ok": False})
        ok_all = False

    if ok_all and not args.skip_digestion and md_path.is_file() and citation_gate_ok and timeline_gate_ok:
        nodes.append(
            _run(
                [
                    PY,
                    str(DIGESTION),
                    "--input",
                    str(md_path),
                    "--topic-slug",
                    f"bigset_{slug}",
                    "--skip-citation-lock",
                    "--skip-active-fact",
                ]
            )
        )
        if not nodes[-1]["ok"]:
            ok_all = False
    else:
        nodes.append(
            {
                "step": "digestion",
                "skipped": True,
                "ok": True,
                "note": "digestion_requires_citation_lock_and_timeline_order_gate_ok",
                "citation_gate_ok": citation_gate_ok,
                "timeline_gate_ok": timeline_gate_ok,
            }
        )

    send_gate = "HOLD"
    completion = {
        "schema": "bigset_ingest_spike_chain_v1",
        "generated_at_utc": _now(),
        "research_only": True,
        "hypothesis_tier": "B",
        "send_gate": send_gate,
        "quality_ok": ok_all,
        "citation_gate_ok": citation_gate_ok,
        "timeline_gate_ok": timeline_gate_ok,
        "promotion_mode": promotion_mode,
        "exit_code": 0 if ok_all else 1,
        "mode": "live" if args.live else "dry_run",
        "cost_tier": "tier_0" if (args.free_tier or not args.live) else "tier_15",
        "free_tier_profile": free_profile,
        "reproducible_command": "py scripts/run_bigset_ingest_spike_chain_v1.py",
        "nodes": nodes,
        "artifact_paths": {
            "bridge": "docs/final/artifacts/bigset_agent_bridge_v1_latest.json",
            "agpl_check": "docs/final/artifacts/bigset_agpl_isolation_wall_v1_latest.json",
            "timeline_repair": "docs/final/artifacts/bigset_tier0_timeline_repair_v1_latest.json",
            "citation_lock": "docs/final/artifacts/bigset_tier0_citation_lock_v1_latest.json",
            "timeline_order": "docs/final/artifacts/bigset_tier0_timeline_order_v1_latest.json",
            "atypical_signal": "docs/final/artifacts/bigset_tier0_atypical_signal_v1_latest.json",
            "human_review_pending": "docs/final/artifacts/bigset_tier0_atypical_human_review_pending_v1_latest.json",
            "human_review_queue": "reports/bigset_tier0_atypical_human_review_queue_v1.jsonl",
            "shadow_rows": "docs/final/artifacts/bigset_tier0_shadow_rows_v1_latest.json",
            "conflict_surface": "docs/final/artifacts/bigset_conflict_surface_v1_latest.json",
            "studio_sidecar": "docs/final/artifacts/bigset_studio_conflict_sidecar_v1_latest.json",
            "studio_mirror": "projects/no1kmedi/public/data/logos_studio/bigset_conflict_sidecar_v1.json",
            "digestion_report": "reports/mkm_digestion_engine_chain_v1_latest.json",
        },
        "downstream": {
            "logos_adoptable_refinery": "py scripts/run_logos_adoptable_spike_chain_v1.py",
            "fusion_chain": "py scripts/run_bigset_logos_fusion_chain_v1.py",
        },
    }

    OUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    OUT_REPORT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    OUT_ARTIFACT.write_text(json.dumps(completion, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": ok_all,
                "citation_gate_ok": citation_gate_ok,
                "timeline_gate_ok": timeline_gate_ok,
                "promotion_mode": promotion_mode,
                "report": str(OUT_REPORT),
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
