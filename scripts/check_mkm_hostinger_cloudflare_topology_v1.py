#!/usr/bin/env python3
"""Verify MKM Hostinger VPS + Cloudflare topology SSOT and local prod ANN mode."""
from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOPO_MD = ROOT / "docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.md"
TOPO_JSON = ROOT / "docs/final/MKM_HOSTINGER_CLOUDFLARE_TOPOLOGY_V1.json"
PROD_SQLITE = ROOT / "docs/final/artifacts/logos_vector_index_ann_lite_v1.sqlite"
DEFAULT_OUT = ROOT / "reports/mkm_infrastructure_topology_check_latest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _prod_embedding_mode() -> str | None:
    if not PROD_SQLITE.is_file():
        return None
    con = sqlite3.connect(str(PROD_SQLITE))
    try:
        row = con.execute(
            "SELECT embedding_mode FROM logos_vec_stub LIMIT 1"
        ).fetchone()
        return str(row[0]) if row else None
    except sqlite3.Error:
        return None
    finally:
        con.close()


def _ssh_ip(host_spec: str, extra_ssh_args: list[str]) -> dict[str, Any]:
    cmd = ["ssh", *extra_ssh_args, host_spec, "hostname -I"]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
    except subprocess.TimeoutExpired:
        return {"host": host_spec, "exit_code": -1, "ips": [], "error": "ssh_timeout"}
    out = (proc.stdout or "").strip().split()
    return {
        "host": host_spec,
        "exit_code": proc.returncode,
        "ips": out[:4] if out else [],
        "error": None if proc.returncode == 0 else (proc.stderr or proc.stdout or "")[-300:],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--output-json", type=Path, default=DEFAULT_OUT)
    ap.add_argument(
        "--ssh-compare",
        action="store_true",
        help="Compare IPs for vps-mkmlife vs MKM_VPS_HOST (needs working ssh keys).",
    )
    ap.add_argument("--ssh-alias", type=str, default="vps-mkmlife")
    ap.add_argument("--ssh-fqdn", type=str, default="")
    args = ap.parse_args()

    topo_json = json.loads(TOPO_JSON.read_text(encoding="utf-8-sig")) if TOPO_JSON.is_file() else {}
    emb = _prod_embedding_mode()
    checks = {
        "topology_md_exists": TOPO_MD.is_file(),
        "topology_json_exists": TOPO_JSON.is_file(),
        "prod_sqlite_exists": PROD_SQLITE.is_file(),
        "prod_is_sentence_transformers": emb == "sentence_transformers_v1",
    }
    ssh_compare: dict[str, Any] | None = None
    if args.ssh_compare:
        fqdn = args.ssh_fqdn.strip()
        if not fqdn:
            print("SKIP ssh-compare: pass --ssh-fqdn or set MKM_VPS_HOST in env", file=sys.stderr)
        else:
            user_host = fqdn if "@" in fqdn else f"root@{fqdn}"
            a = _ssh_ip(args.ssh_alias, [])
            b = _ssh_ip(user_host, [])
            ips_a = set(a.get("ips") or [])
            ips_b = set(b.get("ips") or [])
            ssh_compare = {
                "alias": a,
                "fqdn": b,
                "same_primary_ip": bool(ips_a & ips_b),
                "note": "same_primary_ip=true => one Hostinger VPS; false => investigate before deploy",
            }

    ok = all(
        [
            checks["topology_md_exists"],
            checks["topology_json_exists"],
            checks["prod_sqlite_exists"],
            checks["prod_is_sentence_transformers"],
        ]
    )
    # SSH compare is advisory only (BatchMode/key prompts may hang).
    if args.ssh_compare and ssh_compare and ssh_compare.get("same_primary_ip") is False:
        ok = False

    doc = {
        "schema": "mkm_infrastructure_topology_check_v1",
        "ts_utc": _utc_now(),
        "ok": ok,
        "checks": checks,
        "prod_embedding_mode": emb,
        "topology_one_liner": topo_json.get("one_liner_ko"),
        "ssh_compare": ssh_compare,
        "ssot": str(TOPO_MD.relative_to(ROOT)),
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": ok, "prod_embedding_mode": emb, "out": str(args.output_json)}, ensure_ascii=False))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
