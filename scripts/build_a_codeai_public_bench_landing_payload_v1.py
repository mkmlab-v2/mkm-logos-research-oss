#!/usr/bin/env python3
"""Build a-codeai open-bench landing payload — per-SKU metrics + SEND_GATE HOLD."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_DEFAULT = ROOT / "docs/final/artifacts/a_codeai_public_reproduce_bundle_v1_latest.json"
REPRODUCE_DEFAULT = ROOT / "docs/final/artifacts/compression_public_reproduce_pack_v1_latest.json"
OUT_DEFAULT = ROOT / "docs/final/artifacts/a_codeai_public_bench_landing_payload_v1_latest.json"

PUBLIC_SKU_IDS = (
    "compression_api_open_structured",
    "compression_api_open_structured_long",
    "compression_api_golden40_public_safe",
    "compression_api_golden40_public_safe_routed",
)
INTERNAL_SKU_IDS = (
    "compression_api_track_a_reference",
    "handoff_governance",
    "pilot_roi",
)


def _utc() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _pct(rate: float | None) -> str:
    if rate is None:
        return "n/a"
    return f"{rate * 100:.2f}%"


def _sku_row(sku_id: str, sku: dict[str, Any], *, public: bool) -> dict[str, Any]:
    metrics = sku.get("metrics") or {}
    row: dict[str, Any] = {
        "sku_id": sku_id,
        "public_display": public,
        "role": sku.get("role"),
        "corpus_path": sku.get("corpus_path"),
        "corpus_sha256": sku.get("corpus_sha256"),
        "case_count": metrics.get("case_count"),
        "mean_token_saving_rate_proxy": metrics.get("mean_token_saving_rate_proxy"),
        "mean_jaccard_proxy": metrics.get("mean_jaccard_proxy"),
        "saving_display": _pct(metrics.get("mean_token_saving_rate_proxy")),
        "jaccard_display": (
            f"{metrics.get('mean_jaccard_proxy'):.4f}"
            if isinstance(metrics.get("mean_jaccard_proxy"), (int, float))
            else "n/a"
        ),
        "allowed_headline": sku.get("allowed_headline"),
        "forbidden_headline": sku.get("forbidden_headline"),
    }
    if sku.get("external_sku"):
        row["external_sku"] = sku.get("external_sku")
    if sku.get("forced_shard_id"):
        row["forced_shard_id"] = sku.get("forced_shard_id")
    if sku_id == "compression_api_track_a_reference":
        row["global_token_saving_rate"] = sku.get("global_token_saving_rate")
        row["avg_jaccard"] = sku.get("avg_jaccard")
        row["saving_display"] = _pct(sku.get("global_token_saving_rate"))
        row["jaccard_display"] = (
            f"{sku.get('avg_jaccard'):.4f}" if isinstance(sku.get("avg_jaccard"), (int, float)) else "n/a"
        )
    if sku_id == "handoff_governance":
        row["reduction_percent_vs_full"] = sku.get("reduction_percent_vs_full")
        row["saving_display"] = (
            f"{sku.get('reduction_percent_vs_full'):.2f}%"
            if isinstance(sku.get("reduction_percent_vs_full"), (int, float))
            else "n/a"
        )
    if sku_id == "pilot_roi":
        proxy = sku.get("measured_proxy") or {}
        row["status"] = sku.get("status")
        row["mean_token_saving_rate_proxy"] = proxy.get("mean_token_saving_rate_proxy")
        row["saving_display"] = _pct(proxy.get("mean_token_saving_rate_proxy"))
        row["jaccard_display"] = (
            f"{proxy.get('mean_jaccard_proxy'):.4f}"
            if isinstance(proxy.get("mean_jaccard_proxy"), (int, float))
            else "n/a"
        )
    return row


def build(
    *,
    bundle_path: Path,
    reproduce_path: Path,
) -> dict[str, Any]:
    bundle = _read_json(bundle_path)
    if str(bundle.get("schema")) != "a_codeai_public_reproduce_bundle_v1":
        raise SystemExit("bundle schema mismatch")

    reproduce: dict[str, Any] = {}
    if reproduce_path.is_file():
        reproduce = _read_json(reproduce_path)
    skus = bundle.get("reproduce_pack") or {}

    public_rows = [_sku_row(sid, skus[sid], public=True) for sid in PUBLIC_SKU_IDS if sid in skus]
    internal_rows = [_sku_row(sid, skus[sid], public=False) for sid in INTERNAL_SKU_IDS if sid in skus]

    fail_comp = reproduce.get("fail_comp_004") or [
        "Do not merge open_long % with Track A % with handoff % in one headline",
        "Do not use tenant stub 97.6% as marketing proof",
    ]

    return {
        "schema": "a_codeai_public_bench_landing_payload_v1",
        "generated_at_utc": _utc(),
        "source_bundle": str(bundle_path.relative_to(ROOT)).replace("\\", "/"),
        "git_head": bundle.get("git_head"),
        "send_gate": bundle.get("send_gate", "HOLD"),
        "ready_for_external_send": bool(bundle.get("ready_for_external_send", False)),
        "launch_decision": bundle.get("launch_decision"),
        "launch_pass_count": bundle.get("launch_pass_count"),
        "one_command_reproduce": bundle.get("one_command_reproduce"),
        "reproduce_commands": bundle.get("reproduce_commands") or [],
        "boundary_ack": bundle.get("boundary_ack"),
        "sections": {
            "banner": {
                "status": "SEND_GATE_HOLD",
                "title_ko": "외부 성능 주장 게이트: HOLD",
                "title_en": "External performance claims: SEND_GATE HOLD",
                "body_ko": (
                    "기술 오픈 벤치는 READY(8/8)이나, counsel sign-off 및 실고객 측정 전까지 "
                    "대외 마케팅·보도자료에 SKU 수치를 합쳐 쓰지 마세요."
                ),
                "body_en": (
                    "Technical open-bench is READY (8/8), but external marketing remains HOLD "
                    "until counsel sign-off and real customer measurement. Do not merge SKU metrics."
                ),
            },
            "public_skus": public_rows,
            "internal_skus_do_not_cite": internal_rows,
            "fail_comp_004": fail_comp,
            "deploy_note": bundle.get("deploy_note"),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--bundle-json", type=Path, default=BUNDLE_DEFAULT)
    ap.add_argument("--reproduce-json", type=Path, default=REPRODUCE_DEFAULT)
    ap.add_argument("--out-json", type=Path, default=OUT_DEFAULT)
    args = ap.parse_args()

    bundle_path = args.bundle_json if args.bundle_json.is_absolute() else ROOT / args.bundle_json
    reproduce_path = (
        args.reproduce_json if args.reproduce_json.is_absolute() else ROOT / args.reproduce_json
    )
    out_path = args.out_json if args.out_json.is_absolute() else ROOT / args.out_json

    if not bundle_path.is_file():
        raise SystemExit(f"missing bundle: {bundle_path}")

    doc = build(bundle_path=bundle_path, reproduce_path=reproduce_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "output": str(out_path),
                "public_sku_count": len(doc["sections"]["public_skus"]),
                "send_gate": doc["send_gate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
