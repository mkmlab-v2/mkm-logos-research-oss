#!/usr/bin/env python3
"""Emit infra compliance PHI remediation guide from gate scan — no secret values."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.infra_compliance_gate_v1 import scan_file  # noqa: E402

DEFAULT_ENV = ROOT / ".env"
DEFAULT_OUT = ROOT / "reports/infra_compliance_env_phi_remediation_guide_v1_latest.json"
DEFAULT_ART = ROOT / "docs/final/artifacts/infra_compliance_env_phi_remediation_guide_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_guide(env_path: Path) -> dict[str, Any]:
    result = scan_file(env_path)
    d = result.to_dict()
    phi_reason = "phi_in_sensitive_env_file" in (d.get("reasons") or [])
    cloud_reason = bool(d.get("cloud_hits"))

    steps: list[dict[str, str]] = []
    if phi_reason:
        steps.extend(
            [
                {
                    "step": "1",
                    "action_ko": "`.env`에서 주민등록번호·환자명·SOAP/임상 키를 **삭제**하거나 DPAPI vault로 이전",
                },
                {
                    "step": "2",
                    "action_ko": "개인 식별값은 `scripts/security_agent_manager.py` / LocalLock 경로만 사용 — `.env` 평문 금지",
                },
                {
                    "step": "3",
                    "action_ko": "재검: `py scripts/infra_compliance_gate_v1.py C:\\workspace\\.env` → exit 0 목표",
                },
            ]
        )
    if cloud_reason:
        steps.append(
            {
                "step": "C",
                "action_ko": "Replit/codespaces 토큰·URL을 `.env`에서 제거 — Entry B는 로컬 IDE만",
            }
        )
    if not steps:
        steps.append({"step": "0", "action_ko": "현재 스캔 차단 없음 — 정기 재검만 유지"})

    return {
        "schema": "infra_compliance_env_phi_remediation_guide_v1",
        "generated_at_utc": _utc(),
        "hypothesis_tier": "B",
        "research_only": True,
        "send_gate": "HOLD",
        "scan_path": str(env_path),
        "gate_ok": bool(d.get("ok")),
        "gate_blocked": bool(d.get("blocked")),
        "reasons": d.get("reasons") or [],
        "cloud_hit_count": len(d.get("cloud_hits") or []),
        "phi_hit_count": len(d.get("phi_hits") or []),
        "phi_pattern_labels_only": d.get("phi_hits") or [],
        "remediation_steps": steps,
        "never_paste_in_chat": [
            "phi_hits 원문",
            ".env 값",
            "주민번호 전체",
        ],
        "reproduce": "py scripts/build_infra_compliance_env_phi_remediation_guide_v1.py",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--env-path", type=Path, default=DEFAULT_ENV)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if not args.env_path.is_file():
        print(f"Missing env: {args.env_path}", file=sys.stderr)
        return 2

    doc = build_guide(args.env_path)
    payload = json.dumps(doc, ensure_ascii=False, indent=2) + "\n"
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(payload, encoding="utf-8")
    DEFAULT_ART.parent.mkdir(parents=True, exist_ok=True)
    DEFAULT_ART.write_text(payload, encoding="utf-8")
    print(
        json.dumps(
            {
                "ok": True,
                "gate_blocked": doc["gate_blocked"],
                "phi_hit_count": doc["phi_hit_count"],
                "out": str(args.output_json),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
