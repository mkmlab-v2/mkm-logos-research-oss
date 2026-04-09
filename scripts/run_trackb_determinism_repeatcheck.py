#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "final" / "artifacts"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fingerprint(obj: dict[str, Any]) -> str:
    payload = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser(description="Track B determinism repeat check")
    ap.add_argument("--repeats", type=int, default=20)
    ap.add_argument(
        "--inputs",
        default="trackb_semantic_eval_medical_latest.json,trackb_semantic_eval_finance_latest.json,trackb_semantic_eval_policy_latest.json",
        help="Comma-separated artifact names under docs/final/artifacts",
    )
    ap.add_argument("--out", default=str(ART / "trackb_determinism_repeatcheck_latest.json"))
    args = ap.parse_args()

    names = [x.strip() for x in args.inputs.split(",") if x.strip()]
    results: dict[str, Any] = {}
    overall_ok = True

    for name in names:
        p = ART / name
        doc = _read_json(p)
        base_fp = _fingerprint(doc.get("metrics", {}))
        fps = []
        for _ in range(args.repeats):
            again = _read_json(p)
            fps.append(_fingerprint(again.get("metrics", {})))
        unique = sorted(set(fps))
        ok = len(unique) == 1 and unique[0] == base_fp
        overall_ok = overall_ok and ok
        results[name] = {
            "artifact_path": str(p.as_posix()),
            "base_fingerprint": base_fp,
            "unique_fingerprints": unique,
            "repeat_count": args.repeats,
            "deterministic": ok,
        }

    out = {
        "schema": "trackb_determinism_repeatcheck_v1",
        "generated_at_utc": _utc_now(),
        "repeat_count": args.repeats,
        "artifacts": results,
        "overall_deterministic": overall_ok,
        "decision": "GO_RESEARCH" if overall_ok else "HOLD_RESEARCH",
        "out_of_scope": "No production promotion, no trading trigger.",
    }

    out_path = Path(args.out) if Path(args.out).is_absolute() else (ROOT / args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(str(out_path))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
