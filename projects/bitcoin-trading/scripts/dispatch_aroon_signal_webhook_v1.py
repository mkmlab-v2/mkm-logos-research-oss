#!/usr/bin/env python3
"""Post webhook when Aroon engine signal changes (especially HOLD -> entry)."""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib import error, request

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STATE = ROOT / "logs" / "trading_state.json"
DEFAULT_LAST = ROOT / "memory" / "v2" / "ops" / "aroon_signal_webhook_last_v1.json"
DEFAULT_OUT = ROOT / "memory" / "v2" / "ops" / "aroon_signal_webhook_dispatch_latest.json"


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        o = json.loads(path.read_text(encoding="utf-8-sig"))
    except json.JSONDecodeError:
        return {}
    return o if isinstance(o, dict) else {}


def _signal_from_state(doc: dict[str, Any]) -> str:
    for key in ("last_signal", "signal", "last_signal_summary"):
        v = doc.get(key)
        if v:
            return str(v).strip().upper()
    eng = doc.get("engine") or doc.get("aroon") or {}
    if isinstance(eng, dict) and eng.get("last_signal"):
        return str(eng["last_signal"]).strip().upper()
    return ""


def _post(webhook: str, body: dict[str, Any]) -> tuple[bool, str]:
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        webhook,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=15) as resp:
            return 200 <= int(resp.status) < 300, f"http_{resp.status}"
    except error.HTTPError as e:
        return False, f"http_{e.code}"
    except error.URLError as e:
        return False, f"url_error:{e.reason}"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--trading-state", type=Path, default=DEFAULT_STATE)
    ap.add_argument("--last-json", type=Path, default=DEFAULT_LAST)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--webhook-env", default="OPS_ALARM_WEBHOOK_URL")
    ap.add_argument("--webhook-url", default="")
    ap.add_argument(
        "--dispatch-on-hold",
        action="store_true",
        help="Also webhook when signal changes to HOLD (default: only non-HOLD).",
    )
    args = ap.parse_args()

    state_doc = _load(args.trading_state)
    current = _signal_from_state(state_doc) or "UNKNOWN"
    prev_doc = _load(args.last_json)
    previous = str(prev_doc.get("last_signal") or "").strip().upper()

    changed = current != previous
    actionable = args.dispatch_on_hold or (current not in {"", "UNKNOWN", "HOLD", "INIT"})
    should = changed and actionable

    webhook = str(args.webhook_url or "").strip() or str(os.environ.get(args.webhook_env, "")).strip()

    out: dict[str, Any] = {
        "schema": "aroon_signal_webhook_dispatch_v1",
        "generated_at_utc": _now(),
        "trading_state_path": str(args.trading_state),
        "current_signal": current,
        "previous_signal": previous or None,
        "changed": changed,
        "should_dispatch": should,
        "webhook_configured": bool(webhook),
    }

    if should and webhook:
        body = {
            "source": "aroon_signal_webhook_v1",
            "symbol": state_doc.get("symbol") or "BTCUSDT",
            "previous_signal": previous or None,
            "current_signal": current,
            "enable_trading": state_doc.get("enable_trading"),
            "testnet": state_doc.get("testnet"),
            "note": "Aroon signal change on VPS live stack (small-size profile).",
        }
        ok, reason = _post(webhook, body)
        out["dispatch"] = {"status": "sent" if ok else "failed", "reason": reason}
        if ok:
            prev_doc = {
                "schema": "aroon_signal_webhook_last_v1",
                "last_signal": current,
                "last_dispatched_at_utc": _now(),
            }
            args.last_json.parent.mkdir(parents=True, exist_ok=True)
            args.last_json.write_text(json.dumps(prev_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    elif should and not webhook:
        out["dispatch"] = {"status": "skipped", "reason": "webhook_not_configured"}
    else:
        out["dispatch"] = {"status": "skipped", "reason": "no_actionable_change"}

    if not prev_doc.get("last_signal") and current and not should:
        args.last_json.parent.mkdir(parents=True, exist_ok=True)
        args.last_json.write_text(
            json.dumps(
                {"schema": "aroon_signal_webhook_last_v1", "last_signal": current, "seeded_at_utc": _now()},
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"WROTE: {args.out_json}")
    print(f"signal={current} changed={changed} dispatch={out.get('dispatch')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
