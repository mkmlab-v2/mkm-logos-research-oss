#!/usr/bin/env python3
"""Track C safe copy blocks for LoRA tranche-2 evidence (internal / B2B draft)."""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]

DEFAULT_SIGNOFF = ROOT / "reports/lora_tranche2_signoff_pack_v1_latest.json"
DEFAULT_OUT = ROOT / "docs/final/artifacts/lora_tranche2_trackc_copy_v1_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build_copy(
    signoff: dict[str, Any],
    microtrain: dict[str, Any],
    qwen4: dict[str, Any],
    mp_go: dict[str, Any],
    hybrid12: dict[str, Any],
) -> dict[str, Any]:
    rec = signoff.get("recommendation", {})
    gates = signoff.get("gates", {})
    div = microtrain.get("diversity", {})
    qdiv = qwen4.get("diversity", {})
    qattach = qwen4.get("trained_adapter_attach", {})
    h12div = hybrid12.get("diversity", {})
    multipack_go = mp_go.get("allow_deploy_multipack_btrack") is True
    multipack_line = (
        "GO — bench 4×40 B-track (commander sign-off; Track A·실매매 OFF)"
        if multipack_go
        else rec.get("multi_pack_weight_expansion", "HOLD")
    )

    return {
        "schema": "lora_tranche2_trackc_copy_v1",
        "generated_at_utc": _utc_now(),
        "research_only": True,
        "hypothesis_tag": "[HYPO]",
        "disclaimer_ko": (
            "내부 R&D·제안 초안용. 의료·투자·실거래 단정 아님. "
            "단일 Pack RC와 멀티팩 확장은 별도 게이트."
        ),
        "disclaimer_en": (
            "Internal R&D / draft B2B only. Not medical, investment, or live-trading advice. "
            "Single-pack RC and multi-pack expansion use separate gates."
        ),
        "one_liner_ko": (
            "MKM LoRA 팩토리 1호(RC)는 검증됐고, Golden-40 기준 라우팅은 4×40·MKM12 SSOT는 12×75 hybrid가 "
            "20×200 flat 비전보다 유리합니다[B-track, research_only]."
        ),
        "one_liner_en": (
            "MKM LoRA factory line (RC) is validated; on Golden-40 routing, 4×40 eval alignment and "
            "12×75 hybrid MKM12 SSOT beat the 20×200 flat vision [B-track, research_only]."
        ),
        "bullets_ko": [
            "단일 Pack 0-B RC: human sign-off·allow_deploy(단일 팩 범위).",
            "Tranche 2 라우팅: bench 4×40(평가 SSOT) + hier 12×75 hybrid(MKM12·v61/shard 키워드).",
            "20×200 flat vision: WATCH — 라우팅 모호·ops 비용 대비 이점 미확인.",
            f"Micro-train 3-pack diversity probe: distinct hashes={div.get('distinct_weight_hashes', 'n/a')} (TinyLlama smoke).",
            f"Qwen 4-pack train ablation: distinct hashes={qdiv.get('distinct_weight_hashes', 'n/a')}, attach total={qattach.get('total_attach_sec', 'n/a')}s.",
            f"Hybrid 12-pack micro-train (MKM12 lane): distinct hashes={h12div.get('distinct_weight_hashes', 'n/a')} (TinyLlama smoke).",
            f"Multi-pack production: {multipack_line}.",
        ],
        "bullets_en": [
            "Single Pack 0-B RC: human sign-off / allow_deploy (single-pack scope only).",
            "Tranche 2 routing: bench 4×40 (eval SSOT) + hier 12×75 hybrid (MKM12 + v61/shard keywords).",
            "20×200 flat vision: WATCH — high routing ambiguity; ops cost not justified on current evidence.",
            f"Micro-train 3-pack probe: distinct weight hashes={div.get('distinct_weight_hashes', 'n/a')} (TinyLlama smoke).",
            f"Qwen 4-pack train ablation: distinct hashes={qdiv.get('distinct_weight_hashes', 'n/a')}, attach total={qattach.get('total_attach_sec', 'n/a')}s.",
            f"Hybrid 12-pack micro-train (MKM12 lane): distinct hashes={h12div.get('distinct_weight_hashes', 'n/a')} (TinyLlama smoke).",
            f"Multi-pack production: {multipack_line}.",
        ],
        "gates_excerpt": gates,
        "policy_pointers": {
            "track_c_plan": "docs/final/TRACK_C_IP_BUSINESS_PLAN_2026-04-17.md",
            "public_facing": "docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md",
            "signoff_pack": "docs/final/artifacts/lora_tranche2_signoff_pack_v1_latest.json",
        },
    }


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Build Track C LoRA tranche-2 copy blocks.")
    p.add_argument("--signoff-json", default=str(DEFAULT_SIGNOFF))
    p.add_argument(
        "--microtrain-json",
        default=str(ROOT / "reports/lora_tranche2_microtrain_diversity_probe_latest.json"),
    )
    p.add_argument(
        "--qwen4pack-json",
        default=str(ROOT / "reports/lora_tranche2_qwen4pack_train_ablation_latest.json"),
    )
    p.add_argument(
        "--multipack-go-json",
        default=str(ROOT / "reports/lora_tranche2_multipack_go_no_go_latest.json"),
    )
    p.add_argument(
        "--hybrid12-json",
        default=str(ROOT / "reports/lora_tranche2_hybrid12pack_microtrain_diversity_probe_latest.json"),
    )
    p.add_argument("--out-json", default=str(DEFAULT_OUT))
    return p.parse_args()


def main() -> int:
    args = parse_args()
    signoff = _read_json(Path(args.signoff_json))
    micro = _read_json(Path(args.microtrain_json))
    qwen4 = _read_json(Path(args.qwen4pack_json))
    mp_go = _read_json(Path(args.multipack_go_json))
    hybrid12 = _read_json(Path(args.hybrid12_json))
    doc = build_copy(signoff, micro, qwen4, mp_go, hybrid12)
    out = Path(args.out_json)
    if not out.is_absolute():
        out = ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
