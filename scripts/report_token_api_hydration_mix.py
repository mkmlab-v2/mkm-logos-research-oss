#!/usr/bin/env python3
"""Report Token API hydration mode mix from OpenAPI compress examples.

Writes:
- reports/constitution/btrack_pilot/token_api_hydration_mix_latest.json
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.compression_token_api_stub import app

OPENAPI = ROOT / "docs" / "final" / "openapi_token_compression_stub_v1.yaml"
OUT = ROOT / "reports" / "constitution" / "btrack_pilot" / "token_api_hydration_mix_latest.json"


def _load_yaml() -> Any:
    try:
        import yaml  # type: ignore
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("PyYAML is required: pip install pyyaml") from exc
    return yaml.safe_load(OPENAPI.read_text(encoding="utf-8"))


def main() -> int:
    spec = _load_yaml()
    examples = (
        spec.get("paths", {})
        .get("/v1/compress", {})
        .get("post", {})
        .get("requestBody", {})
        .get("content", {})
        .get("application/json", {})
        .get("examples", {})
    )
    client = TestClient(app)
    rows: list[dict[str, Any]] = []
    by_mode: dict[str, int] = {}
    for example_name, ex in examples.items():
        payload = ex.get("value", {})
        if not isinstance(payload, dict) or "text" not in payload:
            continue
        eval_ctx = payload.get("eval_context") if isinstance(payload.get("eval_context"), dict) else {}
        eval_ctx["hydrate_shadow_compare"] = True
        payload["eval_context"] = eval_ctx
        r = client.post("/v1/compress", json=payload)
        if r.status_code != 200:
            rows.append({"example": example_name, "status_code": r.status_code, "metrics_mode": "error"})
            by_mode["error"] = by_mode.get("error", 0) + 1
            continue
        body = r.json()
        mode = str(body.get("integrity_flags", {}).get("metrics_mode", "unknown"))
        flags = body.get("integrity_flags", {}) or {}
        root_cause = "unknown"
        if mode == "none":
            root_cause = "hydrate_metrics_disabled_or_not_requested"
        elif mode == "decision_fallback":
            if bool(flags.get("hydration_live_eval_elapsed_ms")) and flags.get("shadow_metrics_mode") == "live":
                root_cause = "live_eval_not_requested_in_primary_path"
            else:
                root_cause = "live_eval_unavailable_then_decision_fallback"
        elif mode == "live":
            root_cause = "live_eval_available"
        rows.append(
            {
                "example": example_name,
                "status_code": r.status_code,
                "metrics_mode": mode,
                "hydration_metrics_source": flags.get("hydration_metrics_source"),
                "shadow_mode": flags.get("shadow_mode"),
                "shadow_metrics_mode": flags.get("shadow_metrics_mode"),
                "root_cause": root_cause,
                "savings_ratio": (body.get("compression_metrics") or {}).get("savings_ratio"),
            }
        )
        by_mode[mode] = by_mode.get(mode, 0) + 1
    total = len(rows)
    live = by_mode.get("live", 0)
    report = {
        "schema": "token_api_hydration_mix_v1",
        "ts_utc": datetime.now(timezone.utc).isoformat(),
        "source_openapi": "docs/final/openapi_token_compression_stub_v1.yaml",
        "total_examples": total,
        "metrics_mode_counts": by_mode,
        "root_cause_counts": {
            cause: sum(1 for r in rows if r.get("root_cause") == cause)
            for cause in sorted({str(r.get("root_cause", "unknown")) for r in rows})
        },
        "live_ratio": (live / total) if total else 0.0,
        "rows": rows,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
