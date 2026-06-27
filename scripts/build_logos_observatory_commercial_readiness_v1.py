#!/usr/bin/env python3
"""Track C Logos Observatory commercial readiness gate (local, no network)."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def _root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha16(path: Path) -> str | None:
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16].upper()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--out-json",
        default="reports/logos_observatory_commercial_readiness_v1_latest.json",
    )
    args = parser.parse_args()

    root = _root()
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    checks: list[dict[str, object]] = []

    paths = {
        "v6_html": root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_logos_oracle_v6.html",
        "job_pack_html": root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_logos_job_reading_pack_v1.html",
        "job_pack_slice": root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_job_reading_pack_slice_v1.json",
        "overlay": root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_chronology_overlay_v1.json",
        "dynamic_map": root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_logos_chronology_dynamic_map_v1.json",
        "presets": root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_qa_presets_v1.json",
        "graph_slice": root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/showroom_meaning_topology_graph_slice_v1.json",
        "qa_v2_html": root
        / "projects/bitcoin-trading/ops/windows-rehearsal/jemaai-cloud-mvp/public_showroom_meaning_topology_qa_v2.html",
        "urls": root / "docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json",
        "trace_stub": root / "scripts/logos_trace_api_stub_v1.py",
        "public_smoke": root / "reports/showroom_trust_viz_public_chain_smoke_latest.json",
    }

    for key, path in paths.items():
        checks.append({"id": f"file:{key}", "ok": path.is_file(), "path": str(path.relative_to(root))})

    overlay_sha = _sha16(paths["overlay"])
    dynamic_ok = paths["dynamic_map"].is_file()
    primary_score = None
    primary_era = None
    if dynamic_ok:
        dm = json.loads(paths["dynamic_map"].read_text(encoding="utf-8"))
        ranking = dm.get("era_ranking") or []
        if ranking:
            primary_era = ranking[0].get("era_id")
            primary_score = ranking[0].get("score")

    smoke_ok = False
    if paths["public_smoke"].is_file():
        smoke = json.loads(paths["public_smoke"].read_text(encoding="utf-8"))
        smoke_ok = bool(smoke.get("ok"))

    trace_pytest_ok = False
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_logos_trace_api_stub_v1.py", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    trace_pytest_ok = proc.returncode == 0
    checks.append({"id": "pytest:logos_trace_api_stub", "ok": trace_pytest_ok})

    poc_path = root / "docs/final/artifacts/logos_graph_wire_rag_poc_v1_latest.json"
    poc_honest_ok = False
    poc_metrics: dict[str, float] | None = None
    if poc_path.is_file():
        poc_doc = json.loads(poc_path.read_text(encoding="utf-8"))
        wire = poc_doc.get("wire") or {}
        hm = wire.get("honest_metrics") or {}
        required = (
            "payload_size_ratio",
            "payload_savings_ratio",
            "governance_overhead_factor",
            "envelope_to_wire_factor",
        )
        poc_honest_ok = (
            poc_doc.get("schema") == "logos_graph_wire_rag_poc_v1"
            and all(k in hm for k in required)
            and float(hm.get("payload_size_ratio") or 0) > 0
            and float(hm.get("payload_size_ratio") or 2) < 1.0
            and float(hm.get("governance_overhead_factor") or 0) > 1.0
        )
        if poc_honest_ok:
            poc_metrics = {k: float(hm[k]) for k in required}

    checks.append(
        {
            "id": "poc:honest_wire_metrics",
            "ok": poc_honest_ok,
            "path": str(poc_path.relative_to(root)),
        }
    )

    poc_pytest_ok = False
    poc_proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_build_mkm_graph_wire_rag_poc_v1.py", "-q"],
        cwd=root,
        capture_output=True,
        text=True,
    )
    poc_pytest_ok = poc_proc.returncode == 0
    checks.append({"id": "pytest:graph_wire_rag_poc", "ok": poc_pytest_ok})

    b2b_ok = False
    b2b_report = root / "reports/track_c_b2b_meeting_pack_readiness_v1_latest.json"
    graph_studio_readiness = root / "reports/logos_graph_studio_b2b_meeting_pack_readiness_v1_latest.json"
    b2b_rehearsal = root / "reports/logos_graph_studio_b2b_rehearsal_live_v1_latest.json"
    if b2b_report.is_file():
        b2b = json.loads(b2b_report.read_text(encoding="utf-8"))
        b2b_ok = bool(b2b.get("ready_for_internal_meeting"))
    graph_studio_meeting_ok = False
    if graph_studio_readiness.is_file():
        gs = json.loads(graph_studio_readiness.read_text(encoding="utf-8"))
        graph_studio_meeting_ok = bool(gs.get("ready_for_internal_b2b_meeting"))
    b2b_rehearsal_ok = False
    if b2b_rehearsal.is_file():
        br = json.loads(b2b_rehearsal.read_text(encoding="utf-8"))
        b2b_rehearsal_ok = bool(br.get("ok"))
    checks.append({"id": "b2b_rehearsal_live", "ok": b2b_rehearsal_ok, "path": str(b2b_rehearsal.relative_to(root))})

    hard_ok = all(c["ok"] for c in checks if c["id"].startswith("file:") and c["id"] != "file:public_smoke")
    hard_ok = hard_ok and trace_pytest_ok and poc_honest_ok and poc_pytest_ok

    url_ssot_path = paths["urls"]
    product_primary = "https://logos.jema-ai.com"
    demo_url = "https://jemaai.cloud/public_showroom_meaning_topology_qa_v2.html"
    if url_ssot_path.is_file():
        url_doc = json.loads(url_ssot_path.read_text(encoding="utf-8"))
        cw = url_doc.get("commercial_workspace") or {}
        product_primary = str(cw.get("product_primary_url") or product_primary)
        spine = url_doc.get("logos_demo_spine") or {}
        entry = str(spine.get("entry_point") or "meaning_topology_qa_v2")
        pages = url_doc.get("pages") or {}
        entry_page = pages.get(entry) if isinstance(pages.get(entry), dict) else {}
        demo_url = str(entry_page.get("demo_primary_url") or entry_page.get("canonical") or demo_url)

    report = {
        "schema": "logos_observatory_commercial_readiness_v1",
        "generated_at_utc": generated_at,
        "product_primary_url": product_primary,
        "demo_url": demo_url,
        "demo_spine_ref": "docs/final/artifacts/jemaai_showroom_public_urls_v1_latest.json#logos_demo_spine",
        "legacy_observatory_demo_url": "https://jemaai.cloud/public_showroom_logos_oracle_v6.html?product=1",
        "trace_api_health_url": "https://api.jemaai.cloud/v1/logos/health",
        "overlay_sha256_prefix": overlay_sha,
        "dynamic_map_primary_era_id": primary_era,
        "dynamic_map_primary_score": primary_score,
        "public_smoke_ok": smoke_ok,
        "b2b_meeting_pack_ok": b2b_ok,
        "graph_studio_b2b_meeting_pack_ok": graph_studio_meeting_ok,
        "b2b_graph_studio_rehearsal_ok": b2b_rehearsal_ok,
        "commercial_stack_ok": hard_ok and smoke_ok and b2b_rehearsal_ok and graph_studio_meeting_ok,
        "ready_for_external_send": False,
        "ready_for_external_send_note": "Legal/comms sign-off required; NON_GATING research surface only.",
        "graph_wire_rag_poc_honest_metrics": poc_metrics,
        "checks": checks,
        "hypothesis_tier": "[HYPO]",
        "non_gating": True,
        "no_trading_signal": True,
    }

    out = root / args.out_json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": report["commercial_stack_ok"], "out": str(out)}, ensure_ascii=False))
    return 0 if report["commercial_stack_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
