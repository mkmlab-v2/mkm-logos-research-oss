#!/usr/bin/env python3
"""Batch smoke: B2B demo preset allowlist against logos-research query API.

Reproduce:
  py scripts/check_logos_studio_b2b_demo_preset_batch_v1.py --base http://127.0.0.1:3020
  py scripts/check_logos_studio_b2b_demo_preset_batch_v1.py --base https://logos.jema-ai.com --timeout-s 180
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ALLOWLIST = ROOT / "tests/fixtures/logos_studio_b2b_demo_preset_allowlist_v1.json"
DEFAULT_OUT = ROOT / "reports/logos_studio_b2b_demo_preset_batch_v1_latest.json"


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _post_json(url: str, payload: dict, timeout_s: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "MKM-LogosB2bDemoPresetBatch/1.0",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout_s) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="https://logos.jema-ai.com")
    ap.add_argument("--timeout-s", type=float, default=120.0)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    if not ALLOWLIST.is_file():
        print(f"missing allowlist: {ALLOWLIST}", file=sys.stderr)
        return 2

    spec = json.loads(ALLOWLIST.read_text(encoding="utf-8-sig"))
    preset_ids = spec.get("preset_ids") or []
    default_min_answer = int(spec.get("min_answer_chars") or 80)
    default_min_refs = int(spec.get("min_verse_refs") or 1)
    default_min_hl = int(spec.get("min_highlight_nodes") or 1)
    preset_gates: dict = spec.get("preset_gates") or {}

    def _gate(preset_id: str, key: str, default: int) -> int:
        override = preset_gates.get(preset_id) or {}
        if key in override:
            return int(override[key])
        return default

    base = args.base.rstrip("/")
    query_url = f"{base}/api/logos-research/query"
    failures: list[str] = []
    rows: list[dict] = []

    for preset_id in preset_ids:
        row: dict = {"preset_id": preset_id, "ok": False}
        try:
            body = _post_json(
                query_url,
                {"preset_id": preset_id},
                args.timeout_s,
            )
            if not body.get("ok"):
                failures.append(f"{preset_id}:api_not_ok")
                row["error"] = body.get("error") or "not_ok"
                rows.append(row)
                continue
            result = body.get("result") or {}
            answer_len = len(str(result.get("answer") or ""))
            refs = len((result.get("path") or {}).get("verse_refs") or [])
            hl = len(result.get("highlight_node_ids") or [])
            row.update(
                {
                    "ok": True,
                    "query_mode": result.get("query_mode"),
                    "answer_len": answer_len,
                    "verse_refs": refs,
                    "highlight_nodes": hl,
                }
            )
            if answer_len < _gate(preset_id, "min_answer_chars", default_min_answer):
                failures.append(f"{preset_id}:answer_short_{answer_len}")
                row["ok"] = False
            if refs < _gate(preset_id, "min_verse_refs", default_min_refs):
                failures.append(f"{preset_id}:verse_refs_{refs}")
                row["ok"] = False
            if hl < _gate(preset_id, "min_highlight_nodes", default_min_hl):
                failures.append(f"{preset_id}:highlight_{hl}")
                row["ok"] = False
        except urllib.error.HTTPError as exc:
            failures.append(f"{preset_id}:http_{exc.code}")
            row["error"] = f"http_{exc.code}"
        except Exception as exc:  # noqa: BLE001
            failures.append(f"{preset_id}:{type(exc).__name__}")
            row["error"] = str(exc)[:200]
        rows.append(row)

    out_doc = {
        "schema": "logos_studio_b2b_demo_preset_batch_v1",
        "generated_at_utc": _utc(),
        "base": base,
        "allowlist": str(ALLOWLIST.relative_to(ROOT)).replace("\\", "/"),
        "ok": len(failures) == 0,
        "gate_failures": failures,
        "results": rows,
        "reproduce": f"py scripts/check_logos_studio_b2b_demo_preset_batch_v1.py --base {base} --timeout-s {int(args.timeout_s)}",
    }
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out_doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": out_doc["ok"], "gate_failures": failures, "out": str(out_path)}))
    return 0 if out_doc["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
