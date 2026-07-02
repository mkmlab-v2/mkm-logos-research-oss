"""Logos inquiry PayApp E2E scaffold v1 — dry-run validation (P0-2 · G12 keys excluded)."""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
CONTRACT_REL = "docs/final/artifacts/logos_inquiry_payapp_e2e_contract_v1_latest.json"

REQUIRED_PAYAPP_ROUTES = (
    "projects/no1kmedi/src/app/api/payment/payapp/create/route.ts",
    "projects/no1kmedi/src/app/api/payment/payapp/status/route.ts",
    "projects/no1kmedi/src/app/api/payment/payapp/feedback/route.ts",
    "projects/no1kmedi/src/app/api/logos-research/billing/checkout/route.ts",
)

REQUIRED_INQUIRY_ARTIFACTS = (
    "docs/final/artifacts/logos_inquiry_query_contract_v1_latest.json",
    "docs/final/artifacts/logos_inquiry_stream_contract_v1_latest.json",
    "docs/final/schemas/logos_inquiry_report_v1.schema.json",
)


def load_contract(*, root: Path = ROOT) -> dict[str, Any]:
    path = root / CONTRACT_REL
    if not path.is_file():
        raise FileNotFoundError(CONTRACT_REL)
    return json.loads(path.read_text(encoding="utf-8"))


def prod_keys_present() -> bool:
    return bool(os.environ.get("PAYAPP_KEY") and os.environ.get("PAYAPP_VALUE"))


def build_payapp_create_payload(*, contract: dict[str, Any] | None = None, email: str = "logos-e2e@example.com") -> dict[str, Any]:
    doc = contract or load_contract()
    pro = (doc.get("sku_plans") or {}).get("pro") or {}
    return {
        "email": email,
        "plan_code": pro.get("plan_code") or "logos_inquiry_pro_v1",
        "product_name": pro.get("product_name_ko") or "Logos Inquiry Pro",
        "amount": pro.get("amount_krw_default") or 39000,
        "return_url": doc.get("e2e_flow", {}).get("step_2_create", {}).get("return_url_default")
        or "https://logos.jema-ai.com/logos-research/ask?paid=1",
        "payapp_key": "***REDACTED_G12***",
        "payapp_value": "***REDACTED_G12***",
    }


def validate_scaffold(*, root: Path = ROOT) -> dict[str, Any]:
    contract = load_contract(root=root)
    missing_routes = [p for p in REQUIRED_PAYAPP_ROUTES if not (root / p).is_file()]
    missing_inquiry = [p for p in REQUIRED_INQUIRY_ARTIFACTS if not (root / p).is_file()]
    billing_intent = root / "projects/no1kmedi/src/app/api/logos-research/billing/intent/route.ts"
    payload = build_payapp_create_payload(contract=contract)
    keys_ok = prod_keys_present()

    ok = not missing_routes and not missing_inquiry and billing_intent.is_file()
    return {
        "schema": "logos_inquiry_payapp_e2e_smoke_v1",
        "ok": ok,
        "phase": "P0-2",
        "send_gate": contract.get("send_gate") or "HOLD",
        "mode": "live" if keys_ok else "dry_run_scaffold",
        "prod_keys_present": keys_ok,
        "g12_human_inject_required": True,
        "missing_payapp_routes": missing_routes,
        "missing_inquiry_artifacts": missing_inquiry,
        "billing_intent_route_exists": billing_intent.is_file(),
        "sample_create_payload": payload,
        "plan_code_pro": payload["plan_code"],
        "contract_path": CONTRACT_REL,
        "reproduce": "py scripts/run_logos_inquiry_payapp_e2e_smoke_v1.py",
    }
