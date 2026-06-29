#!/usr/bin/env python3
"""WTT premium CS customer corpus — compression profile / short-cap / flatten ablation [HYPO]."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PY = sys.executable
DEFAULT_CORPUS = ROOT / "data/compression/stateless_poc_prospect_wtt-premium-cs-customer-v1_v1.jsonl"
DEFAULT_OVERLAY = ROOT / "docs/final/artifacts/tenant_wtt-premium-cs-customer-v1_must_keep_overlay_v1.json"
DEFAULT_OUT = ROOT / "reports/wtt_cs_pilot_compression_ablation_v1_latest.json"
ROLE_PREFIX_RE = re.compile(r"\[(?:user|assistant)\]\s*", re.IGNORECASE)

ARMS: list[dict[str, Any]] = [
    {
        "arm_id": "economy_baseline",
        "compression_profile": "economy",
        "short_threshold": None,
        "short_max_saving": None,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "economy_shortcap_30_035",
        "compression_profile": "economy",
        "short_threshold": 30,
        "short_max_saving": 0.35,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "fidelity_baseline",
        "compression_profile": "fidelity",
        "short_threshold": None,
        "short_max_saving": None,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "fidelity_shortcap_30_035",
        "compression_profile": "fidelity",
        "short_threshold": 30,
        "short_max_saving": 0.35,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "economy_shortcap_bodyonly",
        "compression_profile": "economy",
        "short_threshold": 30,
        "short_max_saving": 0.35,
        "corpus_suffix": "bodyonly",
        "strip_role_prefixes": True,
    },
]

EXTENDED_GRID_ARMS: list[dict[str, Any]] = [
    {
        "arm_id": "economy_shortcap_25_030",
        "compression_profile": "economy",
        "short_threshold": 25,
        "short_max_saving": 0.30,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "economy_shortcap_25_035",
        "compression_profile": "economy",
        "short_threshold": 25,
        "short_max_saving": 0.35,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "economy_shortcap_30_030",
        "compression_profile": "economy",
        "short_threshold": 30,
        "short_max_saving": 0.30,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "economy_shortcap_30_040",
        "compression_profile": "economy",
        "short_threshold": 30,
        "short_max_saving": 0.40,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "economy_shortcap_35_035",
        "compression_profile": "economy",
        "short_threshold": 35,
        "short_max_saving": 0.35,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "economy_shortcap_40_035",
        "compression_profile": "economy",
        "short_threshold": 40,
        "short_max_saving": 0.35,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "fidelity_shortcap_25_035",
        "compression_profile": "fidelity",
        "short_threshold": 25,
        "short_max_saving": 0.35,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
    {
        "arm_id": "fidelity_shortcap_35_035",
        "compression_profile": "fidelity",
        "short_threshold": 35,
        "short_max_saving": 0.35,
        "corpus_suffix": None,
        "strip_role_prefixes": False,
    },
]


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def strip_role_prefixes_from_text(text: str) -> str:
    return ROLE_PREFIX_RE.sub("", text).strip()


def build_bodyonly_corpus(source: Path, dest: Path) -> int:
    lines: list[str] = []
    for line in source.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        obj = json.loads(line)
        text = obj.get("text")
        if isinstance(text, str) and text.strip():
            obj["text"] = strip_role_prefixes_from_text(text)
        lines.append(json.dumps(obj, ensure_ascii=False))
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return len(lines)


def _run(cmd: list[str], label: str) -> int:
    print(f"RUN [{label}]", " ".join(cmd))
    proc = subprocess.run(cmd, cwd=str(ROOT), capture_output=True, text=True)
    if proc.stdout.strip():
        print(proc.stdout.strip()[-400:])
    if proc.returncode != 0 and proc.stderr.strip():
        print(proc.stderr.strip()[-400:], file=sys.stderr)
    return proc.returncode


def _read_report(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"missing": True}
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    agg = doc.get("aggregate") or {}
    cc = int(doc.get("case_count") or 0)
    cp = int(doc.get("cases_passed") or 0)
    saving_all = float(agg.get("mean_token_saving_rate_proxy_all_cases") or 0.0)
    jac_all = float(agg.get("mean_jaccard_proxy_all_cases") or 0.0)
    return {
        "case_count": cc,
        "cases_passed": cp,
        "pass_rate": round(cp / cc, 4) if cc else 0.0,
        "mean_saving_all": round(saving_all, 6),
        "mean_jaccard_all": round(jac_all, 6),
        "jaccard_floor": doc.get("jaccard_floor"),
        "parse_or_api_failures": doc.get("parse_or_api_failures"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--corpus-jsonl", type=Path, default=DEFAULT_CORPUS)
    ap.add_argument("--overlay-json", type=Path, default=DEFAULT_OVERLAY)
    ap.add_argument("--tenant-id", default="wtt-premium-cs-customer-v1")
    ap.add_argument("--sku", default="MKM-CHAT-D1")
    ap.add_argument("--max-cases", type=int, default=20)
    ap.add_argument("--short-threshold", type=int, default=30)
    ap.add_argument("--short-max-saving", type=float, default=0.35)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--extended-grid",
        action="store_true",
        help="Append cap/threshold sweep arms (B-track CS short-chat grid).",
    )
    args = ap.parse_args(argv)

    corpus = args.corpus_jsonl.resolve()
    overlay = args.overlay_json.resolve()
    if not corpus.is_file():
        print(f"error: missing corpus: {corpus}", file=sys.stderr)
        return 2

    bodyonly_corpus = corpus.parent / f"{corpus.stem}_bodyonly_v1.jsonl"
    n_body = build_bodyonly_corpus(corpus, bodyonly_corpus)

    arms = list(ARMS)
    if args.extended_grid:
        arms.extend(EXTENDED_GRID_ARMS)

    steps: list[dict[str, Any]] = []
    chain_ok = True

    for arm in arms:
        arm_id = arm["arm_id"]
        threshold = arm["short_threshold"]
        max_saving = arm["short_max_saving"]
        if arm_id.startswith("economy_shortcap") or arm_id.startswith("fidelity_shortcap"):
            if threshold is None:
                threshold = args.short_threshold
            if max_saving is None:
                max_saving = args.short_max_saving

        input_path = bodyonly_corpus if arm.get("strip_role_prefixes") else corpus
        report_rel = f"reports/wtt_cs_pilot_ablation_{arm_id}_v1_latest.json"
        cmd = [
            PY,
            "scripts/run_customer_compression_stateless_poc_v1.py",
            "--input-jsonl",
            input_path.relative_to(ROOT).as_posix(),
            "--sku",
            args.sku,
            "--compression-profile",
            arm["compression_profile"],
            "--max-cases",
            str(args.max_cases),
            "--must-keep-overlay-json",
            overlay.relative_to(ROOT).as_posix(),
            "--out-json",
            report_rel,
            "--relax-pass-gate",
        ]
        if threshold is not None and max_saving is not None:
            cmd.extend(
                [
                    "--short-context-token-threshold",
                    str(threshold),
                    "--short-context-max-saving-rate",
                    str(max_saving),
                ]
            )
        rc = _run(cmd, label=arm_id)
        report_path = ROOT / report_rel
        row = {
            "arm_id": arm_id,
            "compression_profile": arm["compression_profile"],
            "short_context": {
                "token_threshold": threshold,
                "max_saving_rate": max_saving,
            },
            "corpus_path": input_path.relative_to(ROOT).as_posix(),
            "strip_role_prefixes": bool(arm.get("strip_role_prefixes")),
            "exit_code": rc,
            "report_path": report_rel,
            **_read_report(report_path),
        }
        steps.append(row)
        if rc != 0:
            chain_ok = False

    best = max(steps, key=lambda s: (s.get("cases_passed") or 0, s.get("mean_jaccard_all") or 0.0))
    doc = {
        "schema": "wtt_cs_pilot_compression_ablation_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "send_gate": "HOLD",
        "track_a_promotion": False,
        "tenant_id": args.tenant_id,
        "source_corpus": corpus.relative_to(ROOT).as_posix(),
        "bodyonly_corpus": bodyonly_corpus.relative_to(ROOT).as_posix(),
        "bodyonly_row_count": n_body,
        "jaccard_floor": 0.73,
        "chain_ok": chain_ok,
        "arms": steps,
        "best_arm_by_pass_then_jaccard": best.get("arm_id"),
        "note_ko": (
            "CS 실측 20행 B-track ablation only. pass_rate↑ ≠ Track A·SEND·대외 % 승격."
        ),
    }
    out = args.out_json.resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out}")
    print(json.dumps({"chain_ok": chain_ok, "best_arm": best.get("arm_id"), "best_pass": best.get("cases_passed")}))
    return 0 if chain_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
