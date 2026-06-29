#!/usr/bin/env python3
"""Prospect pilot ROI chain: intake → masked JSONL → PoC → metering → ROI report."""

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
TEMPLATE = ROOT / "docs/final/artifacts/compression_b2b_prospect_poc_corpus_intake_v1.template.json"
CORPUS_CANDIDATES = [
    ROOT / "data/compression/stateless_poc_enterprise_50_v1.jsonl",
    ROOT / "data/compression/stateless_poc_open_structured_v1.jsonl",
]
OUT_CHAIN = ROOT / "reports/compression_pilot_roi_chain_v1_latest.json"
OUT_ROI = ROOT / "docs/final/artifacts/compression_b2b_pilot_roi_report_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _rel_path(path: Path) -> str:
    p = path.resolve()
    try:
        return p.relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        return p.as_posix()


def _run(step_id: str, cmd: list[str]) -> dict[str, Any]:
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True, check=False)
    return {
        "id": step_id,
        "cmd": cmd,
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-1500:],
        "stderr_tail": (proc.stderr or "")[-1500:],
    }


def _bootstrap_intake(
    tenant_id: str,
    corpus_path: Path,
    case_count: int,
    *,
    sandbox_mode: bool = False,
) -> Path:
    tpl = json.loads(TEMPLATE.read_text(encoding="utf-8-sig"))
    out = ROOT / f"reports/compression_b2b_prospect_poc_corpus_{tenant_id}_v1.json"
    prev: dict[str, Any] | None = None
    if out.is_file():
        try:
            prev = json.loads(out.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError:
            prev = None
    pilot_intake = bool(
        prev
        and prev.get("status")
        in ("active_pilot_intake", "active_public_open_intake", "active_customer_pilot_intake")
    )
    doc = dict(tpl)
    doc.pop("status", None)
    if sandbox_mode:
        doc["status"] = "active_sandbox_stub"
    elif pilot_intake:
        doc["status"] = prev.get("status") if prev else "active_pilot_intake"
    else:
        doc["status"] = "active_rehearsal"
    doc["tenant_id"] = tenant_id
    doc["activated_at_utc"] = _utc()
    doc["corpus_path"] = corpus_path.relative_to(ROOT).as_posix()
    doc["corpus_case_count"] = case_count
    if pilot_intake and prev:
        doc["labels"] = list(prev.get("labels") or [])
        for key in (
            "corpus_provenance",
            "customer_source_jsonl",
            "blueprint",
            "governance_frozen",
            "recommended_commands",
            "boundary_ack",
            "ready_for_external_send",
            "btrack_poc_options",
        ):
            if key in prev:
                doc[key] = prev[key]
        doc["send_gate"] = prev.get("send_gate", "HOLD")
    elif sandbox_mode:
        labels = ["DRAFT", "research_only", "virtual_sandbox_stub", "solo_self_audit_only"]
        doc["labels"] = labels
        doc["signoff"] = "SOLO_SELF_AUDIT_20260607"
        doc["counsel_signoff"] = False
        doc["ready_for_external_send"] = False
    else:
        doc["labels"] = ["DRAFT", "research_only", "rehearsal_not_customer"]
    if sandbox_mode:
        pass  # labels already set above
    doc["metering"]["tenant_id"] = tenant_id
    doc["metering"]["log_path"] = (
        f"reports/constitution/btrack_pilot/track_a_metering_log_{tenant_id}_v1.jsonl"
    )
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


def _resolve_source_corpus() -> Path:
    for path in CORPUS_CANDIDATES:
        if path.is_file():
            return path
    raise FileNotFoundError(
        "no source corpus; run py scripts/run_compression_evidence_lv1_chain_v1.py first"
    )


def _build_prospect_corpus(tenant_id: str, *, max_cases: int = 25, source: Path | None = None) -> Path:
    src = source or _resolve_source_corpus()
    out = ROOT / f"data/compression/stateless_poc_prospect_{tenant_id}_v1.jsonl"
    lines: list[str] = []
    for i, line in enumerate(src.read_text(encoding="utf-8").splitlines()):
        if not line.strip() or i >= max_cases:
            break
        obj = json.loads(line)
        obj["id"] = f"prospect-{tenant_id}-{i:03d}"
        obj["tenant_id"] = tenant_id
        obj["source"] = f"prospect_rehearsal_masked_from_{src.stem}"
        lines.append(json.dumps(obj, ensure_ascii=False))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _resolve_input_corpus(
    tenant_id: str,
    *,
    input_jsonl: Path | None,
    sandbox_mode: bool,
    max_cases: int,
) -> Path:
    if input_jsonl is None:
        return _build_prospect_corpus(tenant_id, max_cases=max_cases)
    src = (ROOT / input_jsonl).resolve() if not input_jsonl.is_absolute() else input_jsonl.resolve()
    if not src.is_file():
        raise FileNotFoundError(f"missing --input-jsonl: {src}")
    if sandbox_mode:
        out = ROOT / f"data/compression/stateless_poc_open_sandbox_{tenant_id}_v1.jsonl"
        prefix = f"sandbox-{tenant_id}"
        label_source = f"open_sandbox_stub_from_{src.stem}"
    else:
        out = ROOT / f"data/compression/stateless_poc_prospect_{tenant_id}_v1.jsonl"
        prefix = f"prospect-{tenant_id}"
        label_source = f"prospect_rehearsal_masked_from_{src.stem}"
    lines: list[str] = []
    for i, line in enumerate(src.read_text(encoding="utf-8").splitlines()):
        if not line.strip() or i >= max_cases:
            break
        obj = json.loads(line)
        obj["id"] = f"{prefix}-{i:03d}"
        obj["tenant_id"] = tenant_id
        obj["source"] = label_source
        if sandbox_mode:
            obj["virtual_tenant"] = True
            obj["solo_self_audit_only"] = True
            obj["forbidden_as_customer_sla"] = True
            obj["research_only"] = True
        lines.append(json.dumps(obj, ensure_ascii=False))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--tenant-id", default="prospect-rehearsal-01")
    ap.add_argument("--max-cases", type=int, default=30)
    ap.add_argument(
        "--include-calibration",
        action="store_true",
        help="Run Corpus Calibration Pack after ROI report (overlay + hydrate compare).",
    )
    ap.add_argument(
        "--input-jsonl",
        type=Path,
        default=None,
        help="Source public-safe JSONL (masked stub). Sandbox: writes stateless_poc_open_sandbox_<tenant>_v1.jsonl",
    )
    ap.add_argument(
        "--sandbox-mode",
        action="store_true",
        help="Virtual tenant stub — SOLO_SELF_AUDIT only, not customer intake.",
    )
    ap.add_argument(
        "--relax-pass-gate",
        action="store_true",
        help="Pass --relax-pass-gate to stateless PoC runner (research corpora).",
    )
    ap.add_argument(
        "--skip-metering",
        action="store_true",
        help="Skip metering appendix/summary (aux thin host).",
    )
    ap.add_argument("--sku", default=None, help="B2B external SKU (e.g. MKM-CHAT-D1) for forced_shard routing.")
    ap.add_argument(
        "--compression-profile",
        default="economy",
        choices=["economy", "fidelity", "literal"],
        help="V2 compression_profile for stateless PoC.",
    )
    ap.add_argument(
        "--auto-b2b-overlay",
        action="store_true",
        help="Pass --auto-b2b-overlay to stateless PoC when --sku set.",
    )
    ap.add_argument(
        "--must-keep-overlay-json",
        type=Path,
        default=None,
        help="Tenant must_keep overlay JSON for PoC (default: auto if tenant_<id>_must_keep_overlay_v1.json exists).",
    )
    ap.add_argument(
        "--graph-wire-selective-bridge",
        action="store_true",
        help="[HYPO] Pass graph_wire_selective_bridge to stateless PoC.",
    )
    ap.add_argument(
        "--short-context-token-threshold",
        type=int,
        default=None,
        help="[HYPO] V2 short-context cap when token_in_proxy <= threshold.",
    )
    ap.add_argument(
        "--short-context-max-saving-rate",
        type=float,
        default=None,
        help="[HYPO] V2 short-context max saving cap (e.g. 0.35 for CS rows).",
    )
    args = ap.parse_args()

    steps: list[dict[str, Any]] = []
    corpus = _resolve_input_corpus(
        args.tenant_id,
        input_jsonl=args.input_jsonl,
        sandbox_mode=args.sandbox_mode,
        max_cases=args.max_cases,
    )
    intake = _bootstrap_intake(
        args.tenant_id,
        corpus,
        args.max_cases,
        sandbox_mode=args.sandbox_mode,
    )
    steps.append({"id": "bootstrap_intake", "exit_code": 0, "intake": str(intake), "corpus": str(corpus)})

    poc_out = ROOT / f"reports/customer_compression_stateless_poc_{args.tenant_id}_v1_latest.json"
    overlay_json = args.must_keep_overlay_json
    if overlay_json is None:
        guess = ROOT / f"docs/final/artifacts/tenant_{args.tenant_id}_must_keep_overlay_v1.json"
        if guess.is_file():
            overlay_json = guess
    poc_cmd = [
        PY,
        "scripts/run_customer_compression_stateless_poc_v1.py",
        "--input-jsonl",
        corpus.relative_to(ROOT).as_posix(),
        "--max-cases",
        str(args.max_cases),
        "--compression-profile",
        args.compression_profile,
        "--out-json",
        poc_out.relative_to(ROOT).as_posix(),
    ]
    if args.sku:
        poc_cmd.extend(["--sku", args.sku])
    if args.auto_b2b_overlay:
        poc_cmd.append("--auto-b2b-overlay")
    if overlay_json is not None:
        poc_cmd.extend(["--must-keep-overlay-json", _rel_path(Path(overlay_json))])
    if args.graph_wire_selective_bridge:
        poc_cmd.append("--graph-wire-selective-bridge")
    if args.short_context_token_threshold is not None:
        poc_cmd.extend(
            [
                "--short-context-token-threshold",
                str(args.short_context_token_threshold),
            ]
        )
    if args.short_context_max_saving_rate is not None:
        poc_cmd.extend(
            [
                "--short-context-max-saving-rate",
                str(args.short_context_max_saving_rate),
            ]
        )
    if args.relax_pass_gate:
        poc_cmd.append("--relax-pass-gate")
    steps.append(_run("prospect_poc", poc_cmd))

    log_path = ROOT / f"reports/constitution/btrack_pilot/track_a_metering_log_{args.tenant_id}_v1.jsonl"
    if not args.skip_metering:
        steps.append(
            _run(
                "metering_appendix",
                [
                    PY,
                    "scripts/build_compression_b2b_pilot_metering_appendix_v1.py",
                    "--tenant-id",
                    args.tenant_id,
                    "--metering-log",
                    str(log_path),
                    "--seed-demo",
                    "--out",
                    f"docs/final/artifacts/compression_b2b_pilot_metering_appendix_{args.tenant_id}_latest.json",
                ],
            )
        )
        steps.append(
            _run(
                "metering_summary",
                [PY, "scripts/run_track_a_metering_summary.py", "--metering-log", str(log_path)],
            )
        )

    poc = json.loads(poc_out.read_text(encoding="utf-8-sig")) if poc_out.is_file() else {}
    appendix_path = ROOT / f"docs/final/artifacts/compression_b2b_pilot_metering_appendix_{args.tenant_id}_latest.json"
    appendix = json.loads(appendix_path.read_text(encoding="utf-8-sig")) if appendix_path.is_file() else {}
    agg = poc.get("aggregate") or {}
    meter_agg = (appendix.get("metering") or {}).get("aggregate") or {}

    raw_proxy = agg.get("mean_token_saving_rate_proxy")
    raw_jac = agg.get("mean_jaccard_proxy")
    dual_report = {
        "raw": {
            "mean_token_saving_rate_proxy": raw_proxy,
            "mean_jaccard_proxy": raw_jac,
            "rows": poc.get("case_count"),
        },
        "repair_v2": {
            "mean_token_saving_rate_proxy": raw_proxy,
            "mean_jaccard_proxy": raw_jac,
            "repair_applied_count": 0,
            "rows": poc.get("case_count"),
            "note": "stateless_packet harness — no repair processor in this PoC path",
        },
        "delta": {
            "alignment_pass_rate_delta_repair_v2_minus_raw": 0.0,
            "token_saving_rate_delta_repair_v2_minus_raw": 0.0,
        },
    }
    intake_doc = json.loads(intake.read_text(encoding="utf-8-sig"))
    pilot_intake = intake_doc.get("status") in (
        "active_pilot_intake",
        "active_public_open_intake",
        "active_customer_pilot_intake",
    )
    is_public_open = intake_doc.get("status") == "active_public_open_intake"
    is_customer_pilot = intake_doc.get("status") == "active_customer_pilot_intake"
    roi_status = (
        "sandbox_stub_measured"
        if args.sandbox_mode
        else ("pilot_intake_measured" if pilot_intake else "rehearsal_measured_not_customer_dollar")
    )
    roi_doc = {
        "schema": "compression_b2b_pilot_roi_report_v1",
        "generated_at_utc": _utc(),
        "tenant_id": args.tenant_id,
        "status": roi_status,
        "send_gate": "HOLD",
        "ready_for_external_send": False,
        "solo_self_audit": "SOLO_SELF_AUDIT_20260607" if args.sandbox_mode else None,
        "counsel_signoff": False,
        "virtual_tenant": bool(args.sandbox_mode),
        "routing": {
            "sku": args.sku,
            "compression_profile": args.compression_profile,
            "must_keep_overlay_json": _rel_path(Path(overlay_json))
            if overlay_json and Path(overlay_json).is_file()
            else None,
            "graph_wire_selective_bridge": bool(args.graph_wire_selective_bridge),
            "short_context_token_threshold": args.short_context_token_threshold,
            "short_context_max_saving_rate": args.short_context_max_saving_rate,
        },
        "intake_path": intake.relative_to(ROOT).as_posix(),
        "corpus_path": corpus.relative_to(ROOT).as_posix(),
        "poc_report_path": poc_out.relative_to(ROOT).as_posix(),
        "metering_appendix_path": appendix_path.relative_to(ROOT).as_posix()
        if appendix_path.is_file()
        else None,
        "measured_proxy": {
            "case_count": poc.get("case_count"),
            "mean_token_saving_rate_proxy": agg.get("mean_token_saving_rate_proxy"),
            "mean_jaccard_proxy": agg.get("mean_jaccard_proxy"),
            "metering_global_saving_rate": meter_agg.get("global_saving_rate"),
            "events_in_band_40_50": meter_agg.get("events_in_band_40_50"),
        },
        "customer_dollar_roi": None,
        "customer_krw_roi": None,
        "forbidden_as_headline": [
            "Do not cite rehearsal stub as named customer case study",
            "Do not merge with Golden 40 or handoff 99% headlines",
        ],
        "raw_repair_dual_report": dual_report,
        "boundary_ack": (
            "Virtual sandbox stub — SOLO_SELF_AUDIT only; not customer dollar ROI."
            if args.sandbox_mode
            else (
                "Public-open API/RSS pilot — NOT customer corpus; SEND_GATE HOLD."
                if is_public_open
                else (
                    "Customer-masked JSONL pilot — 1:1 ROI proxy only; counsel sign-off required "
                    "before ready_for_external_send; SEND_GATE HOLD."
                    if is_customer_pilot
                    else (
                        "Pilot intake measured with routed SKU — replace corpus with customer-masked JSONL "
                        "before external 1:1 claims; SEND_GATE HOLD."
                        if pilot_intake
                        else "Rehearsal chain only — replace corpus with customer-masked JSONL for real ROI."
                    )
                )
            )
        ),
    }
    OUT_ROI.parent.mkdir(parents=True, exist_ok=True)
    OUT_ROI.write_text(json.dumps(roi_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    steps.append({"id": "pilot_roi_report", "exit_code": 0, "output": str(OUT_ROI)})

    if args.include_calibration:
        cal_cmd = [
            PY,
            "scripts/run_compression_calibration_pack_v1.py",
            "--tenant-id",
            args.tenant_id,
            "--input-jsonl",
            corpus.relative_to(ROOT).as_posix(),
            "--max-cases",
            str(args.max_cases),
            "--skip-dollar-roi",
        ]
        steps.append(_run("corpus_calibration_pack", cal_cmd))

    failed = [s for s in steps if s.get("exit_code", 0) != 0]
    chain_doc = {
        "schema": "compression_pilot_roi_chain_v1",
        "generated_at_utc": _utc(),
        "chain_ok": len(failed) == 0,
        "tenant_id": args.tenant_id,
        "sandbox_mode": bool(args.sandbox_mode),
        "solo_self_audit": "SOLO_SELF_AUDIT_20260607" if args.sandbox_mode else None,
        "steps": steps,
        "roi_report": OUT_ROI.relative_to(ROOT).as_posix(),
    }
    OUT_CHAIN.write_text(json.dumps(chain_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"chain_ok": chain_doc["chain_ok"], "failed": [s["id"] for s in failed]}, ensure_ascii=False))
    return 0 if chain_doc["chain_ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
