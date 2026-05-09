#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DROP = ROOT / "reports" / "news_repro" / "latest"
OUT = ROOT / "docs" / "final" / "artifacts" / "news_repro_dropzone_validation_latest.json"

PLACEHOLDER_MARKERS = [
    "PLACEHOLDER_TEMPLATE_ONLY",
    "REPLACE_WITH_REAL_",
    "placeholder template",
    "SIMULATED_INTERNAL_NOT_THIRD_PARTY",
]
DISALLOWED_IDS = {
    "",
    "external-runner-auto",
    "external-runner-unknown",
    "simulated-from-internal",
    "external-signer-auto",
    "external-signer-unknown",
    "simulated-signer",
}


def has_placeholder(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return True
    low = text.lower()
    return any(m.lower() in low for m in PLACEHOLDER_MARKERS)


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    for enc in ("utf-8", "utf-8-sig"):
        try:
            return json.loads(path.read_text(encoding=enc))
        except Exception:
            continue
    return {}


def check_manifest(path: Path) -> list[str]:
    issues: list[str] = []
    doc = read_json(path)
    runner_id = str(doc.get("runner_id", "")).strip()
    if runner_id in DISALLOWED_IDS:
        issues.append("runner_id is missing or still placeholder/simulated")
    return issues


def check_raw_log(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ["cannot read raw benchmark log"]
    lines = [ln for ln in text.splitlines() if ln.strip()]
    if len(lines) < 3:
        issues.append("raw log has too few non-empty lines")
    low = text.lower()
    if "simulated" in low or "template" in low:
        issues.append("raw log still contains simulated/template wording")
    return issues


def check_digest(path: Path) -> list[str]:
    issues: list[str] = []
    doc = read_json(path)
    runner_id = str(doc.get("runner_id", "")).strip()
    signer = str(((doc.get("signature") or {}).get("signer", ""))).strip()
    if runner_id in DISALLOWED_IDS:
        issues.append("digest.runner_id is missing or placeholder/simulated")
    if signer in DISALLOWED_IDS:
        issues.append("digest.signature.signer is missing or placeholder/simulated")
    metrics = doc.get("metrics") or {}
    for key in ("saving", "jaccard", "integrity"):
        if metrics.get(key) is None:
            issues.append(f"digest.metrics.{key} is missing")
    return issues


def check_signed_statement(path: Path) -> list[str]:
    issues: list[str] = []
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ["cannot read signed reproducibility statement"]
    low = text.lower()
    if "simulated" in low or "template" in low:
        issues.append("signed statement still contains simulated/template wording")
    if "independent" not in low and "third-party" not in low and "third party" not in low:
        issues.append("signed statement does not mention independent/third-party verification")
    return issues


def main() -> int:
    files = {
        "external_runner_manifest.json": DROP / "external_runner_manifest.json",
        "raw_benchmark.log": DROP / "raw_benchmark.log",
        "independent_result_digest.json": DROP / "independent_result_digest.json",
        "signed_repro_statement.txt": DROP / "signed_repro_statement.txt",
    }

    checks = {}
    for name, path in files.items():
        issues: list[str] = []
        if name == "external_runner_manifest.json":
            issues.extend(check_manifest(path))
        elif name == "raw_benchmark.log":
            issues.extend(check_raw_log(path))
        elif name == "independent_result_digest.json":
            issues.extend(check_digest(path))
        elif name == "signed_repro_statement.txt":
            issues.extend(check_signed_statement(path))
        checks[name] = {
            "path": str(path),
            "exists": path.exists(),
            "placeholder_detected": has_placeholder(path),
            "issues": issues,
        }

    all_present = all(v["exists"] for v in checks.values())
    no_placeholders = all((not v["placeholder_detected"]) for v in checks.values())
    no_issues = all(len(v["issues"]) == 0 for v in checks.values())
    ready = all_present and no_placeholders and no_issues

    payload = {
        "schema": "news_repro_dropzone_validation_v1",
        "dropzone": str(DROP),
        "checks": checks,
        "summary": {
            "all_present": all_present,
            "no_placeholders": no_placeholders,
            "no_issues": no_issues,
            "ready_for_apply": ready,
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(str(OUT))
    return 0 if ready else 2


if __name__ == "__main__":
    raise SystemExit(main())

