#!/usr/bin/env python3
"""Build ordered registrar-transfer playbook from readiness JSON (human steps only)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_READINESS = ROOT / "reports" / "hostinger_registrar_transfer_readiness_latest.json"
DEFAULT_OUT = ROOT / "reports" / "hostinger_registrar_transfer_playbook_latest.json"

OPS_PRIORITY = {
    "jema-ai.com": 10,
    "jemaai.cloud": 20,
    "no1kmedi.com": 30,
    "mkmlife.com": 40,
    "jema12.com": 50,
    "personadiary.com": 60,
    "a-codeai.com": 70,
    "mkmlab.space": 80,
}

HUMAN_STEPS_TRANSFER = [
    "Hostinger hPanel: 도메인 잠금 해제(lock_released)",
    "Hostinger: EPP/인증코드 발급(epp_received) — 레포·채팅에 코드 저장 금지",
    "Cloudflare Dashboard → Registrar → Transfer domain → 코드 제출",
    "이전 완료 확인 후 scripts/data/hostinger_full_exit/registrar_transfer_tracker_v1.json 불리언만 갱신",
]

HUMAN_STEPS_NS_FIRST = [
    "Cloudflare에 zone 추가(미존재 시) → NS 레코드 확인",
    "Hostinger(현재 레지스트라): 네임서버를 Cloudflare NS로 변경",
    "전파 확인: scripts/Invoke-HostingerRegistrarTransferReadiness_v1.ps1 → delegation_evidence_ok",
    "이후 HUMAN_STEPS_TRANSFER 동일",
]


def _wave_for(row: dict) -> tuple[int, str]:
    apex = row["apex"]
    if row.get("cf_active_zone_found") and row.get("delegation_evidence_ok"):
        return 1, "wave1_cf_zone_active"
    if row.get("delegation_evidence_ok") and not row.get("cf_active_zone_found"):
        return 2, "wave2_cf_ns_zone_pending"
    return 3, "wave3_ns_to_cloudflare_first"


def main() -> int:
    readiness_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_READINESS
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT
    if not readiness_path.is_file():
        print(f"Missing readiness: {readiness_path}", file=sys.stderr)
        return 1
    data = json.loads(readiness_path.read_text(encoding="utf-8-sig"))
    domains_in = data.get("domains") or []

    waves: dict[int, dict] = {
        1: {
            "wave": 1,
            "label_ko": "운영 핵심 — CF NS + active zone (레지스트라 이전만 남음)",
            "wave_id": "wave1_cf_zone_active",
            "domains": [],
            "human_steps": list(HUMAN_STEPS_TRANSFER),
        },
        2: {
            "wave": 2,
            "label_ko": "CF NS 있음 — zone active 확인·추가 후 이전",
            "wave_id": "wave2_cf_ns_zone_pending",
            "domains": [],
            "human_steps": [
                "Cloudflare Dashboard → 해당 apex zone 상태 active 확인(없으면 zone 추가)",
            ]
            + list(HUMAN_STEPS_TRANSFER),
        },
        3: {
            "wave": 3,
            "label_ko": "dns-parking — CF NS 전환 선행",
            "wave_id": "wave3_ns_to_cloudflare_first",
            "domains": [],
            "human_steps": list(HUMAN_STEPS_NS_FIRST),
        },
    }

    for row in domains_in:
        if row.get("transfer_completed"):
            continue
        wnum, wid = _wave_for(row)
        waves[wnum]["domains"].append(
            {
                "apex": row["apex"],
                "ops_priority": OPS_PRIORITY.get(row["apex"], 99),
                "ns_includes_cloudflare": row.get("ns_includes_cloudflare"),
                "cf_active_zone_found": row.get("cf_active_zone_found"),
                "delegation_evidence_ok": row.get("delegation_evidence_ok"),
                "transfer_ready_guess": row.get("transfer_ready_guess"),
            }
        )

    for w in waves.values():
        w["domains"].sort(key=lambda d: d["ops_priority"])

    ordered_waves = [waves[k] for k in sorted(waves) if waves[k]["domains"]]

    payload = {
        "schema": "hostinger_registrar_transfer_playbook_v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "target_registrar": data.get("target_registrar", "Cloudflare Registrar"),
        "readiness_path": str(readiness_path),
        "tracker_path": str(
            ROOT / "scripts" / "data" / "hostinger_full_exit" / "registrar_transfer_tracker_v1.json"
        ),
        "recommended_sequence": ordered_waves,
        "cloudflare_cache_purge": {
            "recommended_first": True,
            "script": "scripts/Invoke-CloudflareCachePurge_v1.ps1",
            "token_permission": "Zone · Cache Purge · Purge (DNS-only token returns 401)",
            "zones_default": ["jema-ai.com", "jemaai.cloud"],
            "manual_fallback": "Cloudflare Dashboard → Caching → Configuration → Purge Everything (per zone)",
        },
        "hostinger_decommission": {
            "gate_report": "reports/hostinger_decommission_gate_latest.json",
            "note": "모든 필수 도메인 wave1–2 이전 완료 후 hPanel 백업·호스팅 해지(인간). VPS 유지.",
        },
    }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {out_path}")
    for w in ordered_waves:
        names = ", ".join(d["apex"] for d in w["domains"])
        print(f"  Wave {w['wave']}: {names}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
