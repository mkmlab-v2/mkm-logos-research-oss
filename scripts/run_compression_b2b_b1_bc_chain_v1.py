#!/usr/bin/env python3
"""B1(B+C): must_keep overlay + corpus 30 + loss-profile A/B for B2B industry SKUs. [HYPO]"""

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
ROWS_PER_SKU = 30
LOSS_PROFILES = ("semantic_general", "code_equivalent")

SKU_CORPUS: dict[str, str] = {
    "MKM-SCM-A1": "data/compression/stateless_poc_scm_public_safe_v1.jsonl",
    "MKM-CHAT-D1": "data/compression/stateless_poc_chat_public_safe_v1.jsonl",
    "MKM-FIN-E1": "data/compression/stateless_poc_finance_public_safe_v1.jsonl",
    "MKM-MED-G1": "data/compression/stateless_poc_health_public_safe_v1.jsonl",
}

DEFAULT_OUT = ROOT / "reports/compression_b2b_b1_bc_chain_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _run(cmd: list[str], *, label: str) -> tuple[int, str, str]:
    print(f"RUN [{label}]", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.stdout.strip():
        print(proc.stdout.strip()[-800:])
    if proc.returncode != 0 and proc.stderr.strip():
        print(proc.stderr.strip()[-800:], file=sys.stderr)
    return proc.returncode, proc.stdout, proc.stderr


def _read_agg(report: Path) -> dict[str, Any]:
    if not report.is_file():
        return {}
    doc = json.loads(report.read_text(encoding="utf-8-sig"))
    agg = doc.get("aggregate") or {}
    cc = doc.get("case_count") or 0
    cp = doc.get("cases_passed") or 0
    return {
        "case_count": cc,
        "cases_passed": cp,
        "pass_rate": round(cp / cc, 4) if cc else 0.0,
        "mean_token_saving_rate_proxy": agg.get("mean_token_saving_rate_proxy"),
        "mean_jaccard_proxy": agg.get("mean_jaccard_proxy"),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--rows-per-sku", type=int, default=ROWS_PER_SKU)
    ap.add_argument("--skip-corpus", action="store_true")
    ap.add_argument("--skip-hydrate", action="store_true")
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    chain_ok = True

    if not args.skip_corpus:
        rc, _, _ = _run(
            [PY, "scripts/build_compression_b2b_industry_poc_corpus_v1.py", "--rows-per-sku", str(args.rows_per_sku)],
            label="corpus_30",
        )
        steps.append({"step": "build_corpus", "exit_code": rc, "rows_per_sku": args.rows_per_sku})
        if rc != 0:
            chain_ok = False

    overlay_steps: list[dict[str, Any]] = []
    hydrate_steps: list[dict[str, Any]] = []
    loss_profile_runs: list[dict[str, Any]] = []

    for sku, corpus_rel in SKU_CORPUS.items():
        corpus = ROOT / corpus_rel
        slug = sku.lower().replace("mkm-", "")
        overlay_out = ROOT / f"docs/final/artifacts/b2b_sku_{slug}_must_keep_overlay_v1.json"

        rc, _, _ = _run(
            [
                PY,
                "scripts/build_b2b_sku_must_keep_overlay_v1.py",
                "--external-sku",
                sku,
                "--input-jsonl",
                corpus_rel,
                "--out-json",
                overlay_out.relative_to(ROOT).as_posix(),
            ],
            label=f"overlay_{slug}",
        )
        overlay_steps.append({"external_sku": sku, "overlay_path": overlay_out.as_posix(), "exit_code": rc})
        if rc != 0:
            chain_ok = False

        if not args.skip_hydrate and overlay_out.is_file():
            hydrate_out = ROOT / f"reports/compression_pilot_hydrate_compare_b2b_{slug}_v1_latest.json"
            rc, _, _ = _run(
                [
                    PY,
                    "scripts/run_compression_pilot_hydrate_compare_v1.py",
                    "--tenant-id",
                    f"b2b-{slug.replace('-', '_')}",
                    "--input-jsonl",
                    corpus_rel,
                    "--overlay-json",
                    overlay_out.relative_to(ROOT).as_posix(),
                    "--max-cases",
                    str(args.rows_per_sku),
                    "--out-json",
                    hydrate_out.relative_to(ROOT).as_posix(),
                ],
                label=f"hydrate_{slug}",
            )
            hydrate_doc: dict[str, Any] = {}
            if hydrate_out.is_file():
                hydrate_doc = json.loads(hydrate_out.read_text(encoding="utf-8-sig"))
            hydrate_steps.append(
                {
                    "external_sku": sku,
                    "exit_code": rc,
                    "report_path": hydrate_out.as_posix(),
                    "baseline_jaccard": (hydrate_doc.get("baseline") or {}).get("mean_jaccard_proxy"),
                    "overlay_jaccard": (hydrate_doc.get("overlay_on") or {}).get("mean_jaccard_proxy"),
                    "delta_jaccard_pp": (hydrate_doc.get("delta") or {}).get("jaccard_pp_overlay_minus_baseline"),
                }
            )
            if rc != 0:
                chain_ok = False

    for loss_profile in LOSS_PROFILES:
        bundle_out = ROOT / f"reports/compression_b2b_sku_industry_poc_bundle_{loss_profile}_v1_latest.json"
        for sku, corpus_rel in SKU_CORPUS.items():
            slug = sku.lower().replace("mkm-", "").replace("-", "_")
            report = ROOT / f"reports/customer_compression_stateless_poc_{slug}_{loss_profile}_v1_latest.json"
            cmd = [
                PY,
                "scripts/run_customer_compression_stateless_poc_v1.py",
                "--input-jsonl",
                corpus_rel,
                "--sku",
                sku,
                "--max-cases",
                str(args.rows_per_sku),
                "--loss-profile",
                loss_profile,
                "--out-json",
                report.relative_to(ROOT).as_posix(),
                "--relax-pass-gate",
            ]
            rc, _, _ = _run(cmd, label=f"poc_{slug}_{loss_profile}")
            loss_profile_runs.append(
                {
                    "external_sku": sku,
                    "loss_profile": loss_profile,
                    "exit_code": rc,
                    "report_path": report.as_posix(),
                    **_read_agg(report),
                }
            )
            if rc != 0:
                chain_ok = False

        # Write bundle summary for this loss profile (semantic_general is primary SSOT)
        bundle_steps = [r for r in loss_profile_runs if r["loss_profile"] == loss_profile]
        bundle_doc = {
            "schema": "compression_b2b_sku_industry_poc_bundle_v1",
            "generated_at_utc": _utc(),
            "research_only": True,
            "send_gate": "HOLD",
            "loss_profile": loss_profile,
            "rows_per_sku": args.rows_per_sku,
            "bundle_ok": all(s.get("exit_code") == 0 for s in bundle_steps),
            "steps": bundle_steps,
        }
        bundle_out.write_text(json.dumps(bundle_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        if loss_profile == "semantic_general":
            primary = ROOT / "reports/compression_b2b_sku_industry_poc_bundle_v1_latest.json"
            primary.write_text(json.dumps(bundle_doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    rc, _, _ = _run(
        [PY, "scripts/build_compression_b2b_industry_sku_gap_report_v1.py"],
        label="gap_report",
    )
    steps.append({"step": "gap_report", "exit_code": rc})
    if rc != 0:
        chain_ok = False

    gap_path = ROOT / "reports/compression_b2b_industry_sku_gap_report_v1_latest.json"
    gap_doc = json.loads(gap_path.read_text(encoding="utf-8-sig")) if gap_path.is_file() else {}

    doc = {
        "schema": "compression_b2b_b1_bc_chain_v1",
        "generated_at_utc": _utc(),
        "action": "EXECUTE_B1_B_PLUS_C",
        "send_gate": "HOLD",
        "ad_headline_ready": False,
        "ready_for_external_send": False,
        "labels": ["HYPO", "research_only", "proof_sprint_lv3"],
        "rows_per_sku": args.rows_per_sku,
        "loss_profiles": list(LOSS_PROFILES),
        "chain_ok": chain_ok,
        "overlay_steps": overlay_steps,
        "hydrate_steps": hydrate_steps,
        "loss_profile_runs": loss_profile_runs,
        "gap_report_path": gap_path.as_posix() if gap_path.is_file() else None,
        "gap_summary": gap_doc.get("summary"),
        "boundary_ack": "must_keep overlay via hydrate arm; keyword-only Option A not executed.",
    }
    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(json.dumps({"chain_ok": chain_ok, "output": str(out)}, ensure_ascii=False))
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
