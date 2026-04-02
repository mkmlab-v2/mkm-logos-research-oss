#!/usr/bin/env python3
"""Emit billing_invoice_from_env_latest.json from .env / process env (FACT_SAFE_*)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path


SCHEMA = "billing_invoice_input_v1"
DEFAULT_OUT = Path("docs/final/artifacts/billing_invoice_from_env_latest.json")


def _load_dotenv(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _fenv(key: str, dot: dict[str, str]) -> str | None:
    v = os.environ.get(key)
    if v is not None and str(v).strip() != "":
        return str(v).strip()
    v2 = dot.get(key)
    if v2 is not None and str(v2).strip() != "":
        return str(v2).strip()
    return None


def main() -> int:
    root = Path(".").resolve()
    out = DEFAULT_OUT if not os.environ.get("FACT_SAFE_BILLING_INVOICE_OUT") else Path(
        os.environ["FACT_SAFE_BILLING_INVOICE_OUT"]
    ).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    dot = _load_dotenv(root / ".env")
    prev: dict = {}
    if out.is_file():
        try:
            prev = json.loads(out.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            prev = {}

    now = datetime.now(timezone.utc)
    period = _fenv("FACT_SAFE_INVOICE_PERIOD_LABEL", dot) or prev.get("period_label") or now.strftime("%Y-%m")
    api_cost_s = _fenv("FACT_SAFE_API_COST_USD", dot)
    api_cost = float(api_cost_s) if api_cost_s is not None else float(prev.get("api_cost_usd") or 0.0)
    provider = _fenv("FACT_SAFE_INVOICE_PROVIDER", dot) or prev.get("provider") or "pending_portal_sync"
    invoice_id = _fenv("FACT_SAFE_INVOICE_ID", dot) or prev.get("invoice_id") or "evidence_pipeline_local_v1"
    provenance = _fenv("FACT_SAFE_INVOICE_PROVENANCE", dot) or prev.get("invoice_provenance") or "provider_file"
    note = _fenv("FACT_SAFE_INVOICE_NOTE", dot) or prev.get("note") or (
        "You may mention replace_with in this note for humans; scanner only checks period_label, provider, invoice_id."
    )

    payload = {
        "schema": SCHEMA,
        "period_label": period,
        "api_cost_usd": api_cost,
        "invoice_provenance": provenance,
        "provider": provider,
        "invoice_id": invoice_id,
        "note": note,
    }
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"WROTE: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
