#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check MUTDA News OPEN_BETA deployment ACK walls."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs/final/artifacts/mudda_mutda_news_open_beta_deployment_ack_v0_1_latest.json"


def main() -> int:
    fails: list[str] = []
    if not OUT.is_file():
        print(json.dumps({"ok": False, "fails": ["missing"]}))
        return 1
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    if doc.get("commander_ack") != "COMMANDER_MUTDA_NEWS_OPEN_BETA_DEPLOYMENT_ACK":
        fails.append("ack")
    if doc.get("MISSION") != "MKM_MUTDA_NEWS_OPEN_BETA_V1":
        fails.append("mission")
    auth = set(doc.get("AUTHORIZED") or [])
    for t in ("production_deploy_mutda_ai", "frontend_minimal_shell", "ep01_publish_on_mutda_news"):
        if t not in auth:
            fails.append(f"auth:{t}")
    forb = set(doc.get("NOT_AUTHORIZED") or [])
    for t in (
        "paid_ads",
        "redirect_acodeai_jema_mkmlife_logos_to_mutda",
        "product_done",
        "decision_os_superiority_claim",
    ):
        if t not in forb:
            fails.append(f"forbid:{t}")
    if doc.get("PRODUCT_DONE") is not False or doc.get("send_gate") != "HOLD":
        fails.append("product")
    if (doc.get("labels") or {}).get("CURRENT_MAINLINE_REPLACEMENT") is not False:
        fails.append("mainline")
    ok = not fails
    print(
        json.dumps(
            {
                "ok": ok,
                "MISSION": doc.get("MISSION"),
                "PRODUCT_DONE": False,
                "send_gate": "HOLD",
                "fails": fails,
            },
            ensure_ascii=False,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
