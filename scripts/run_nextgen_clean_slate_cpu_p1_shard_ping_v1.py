#!/usr/bin/env python3
"""P1: distributed shard ping — fake weight block transfer + remote digest (research_only)."""
from __future__ import annotations

import argparse
import hashlib
import json
import socket
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/p1_shard_ping_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _recv_exact(conn: socket.socket, n: int) -> bytes | None:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def _digest_shard(shard_index: int, payload: bytes) -> bytes:
    return hashlib.sha256(payload + struct.pack("!I", shard_index)).digest()


def _serve(port: int) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(5)
    print(f"[p1-server] listening 0.0.0.0:{port}", flush=True)
    try:
        while True:
            conn, addr = sock.accept()
            with conn:
                hdr = _recv_exact(conn, 8)
                if not hdr:
                    continue
                shard_index, length = struct.unpack("!II", hdr)
                payload = _recv_exact(conn, length)
                if payload is None:
                    continue
                digest = _digest_shard(shard_index, payload)
                conn.sendall(digest)
                print(
                    f"[p1-server] shard={shard_index} bytes={length} from {addr[0]}",
                    flush=True,
                )
    except KeyboardInterrupt:
        print("[p1-server] stopped", flush=True)
        return 0
    finally:
        sock.close()


def _client_ping(
    host: str,
    port: int,
    shard_index: int,
    payload_kb: int,
) -> dict[str, Any]:
    payload = bytes(payload_kb * 1024)
    start = time.perf_counter()
    with socket.create_connection((host, port), timeout=8.0) as conn:
        hdr = struct.pack("!II", shard_index, len(payload))
        conn.sendall(hdr + payload)
        digest = _recv_exact(conn, 32)
        if not digest:
            raise RuntimeError("empty digest")
        expected = _digest_shard(shard_index, payload)
        if digest != expected:
            raise RuntimeError("digest mismatch")
    elapsed_ms = (time.perf_counter() - start) * 1000.0
    return {
        "shard_index": shard_index,
        "payload_kb": payload_kb,
        "elapsed_ms": round(elapsed_ms, 3),
        "digest_hex": digest.hex()[:16],
    }


def _loopback_run(port: int, shard_index: int, rounds: int, payload_kb: int) -> dict:
    import threading

    ready = threading.Event()

    def _runner() -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(("127.0.0.1", port))
        sock.listen(1)
        ready.set()
        for _ in range(rounds):
            conn, _ = sock.accept()
            with conn:
                hdr = _recv_exact(conn, 8)
                if not hdr:
                    break
                sidx, length = struct.unpack("!II", hdr)
                payload = _recv_exact(conn, length)
                if payload is None:
                    break
                conn.sendall(_digest_shard(sidx, payload))
        sock.close()

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    if not ready.wait(timeout=5.0):
        raise RuntimeError("p1 loopback server timeout")
    time.sleep(0.05)
    rows = []
    for _ in range(rounds):
        rows.append(_client_ping("127.0.0.1", port, shard_index, payload_kb))
    t.join(timeout=5.0)
    elapsed = [r["elapsed_ms"] for r in rows]
    return {
        "mode": "loopback",
        "host": "127.0.0.1",
        "rounds": rounds,
        "payload_kb": payload_kb,
        "shard_index": shard_index,
        "elapsed_ms": {
            "p50": round(sorted(elapsed)[len(elapsed) // 2], 3),
            "max": round(max(elapsed), 3),
            "mean": round(sum(elapsed) / len(elapsed), 3),
        },
        "samples": rows[:3],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--mode",
        choices=["server", "client", "loopback"],
        default="loopback",
    )
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=19877)
    ap.add_argument("--shard-index", type=int, default=1)
    ap.add_argument("--rounds", type=int, default=10)
    ap.add_argument("--payload-kb", type=int, default=256)
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.mode == "server":
        return _serve(args.port)

    if args.mode == "loopback":
        body = _loopback_run(args.port, args.shard_index, args.rounds, args.payload_kb)
    elif args.mode == "client":
        rows = []
        errors = 0
        for _ in range(max(1, args.rounds)):
            try:
                rows.append(
                    _client_ping(args.host, args.port, args.shard_index, args.payload_kb)
                )
            except OSError:
                errors += 1
        elapsed = [r["elapsed_ms"] for r in rows]
        body = {
            "mode": "client",
            "host": args.host,
            "port": args.port,
            "rounds_requested": args.rounds,
            "rounds_ok": len(rows),
            "errors": errors,
            "payload_kb": args.payload_kb,
            "shard_index": args.shard_index,
            "elapsed_ms": {
                "p50": round(sorted(elapsed)[len(elapsed) // 2], 3) if elapsed else None,
                "p95": round(
                    sorted(elapsed)[max(0, int(0.95 * (len(elapsed) - 1)))], 3
                )
                if elapsed
                else None,
                "max": round(max(elapsed), 3) if elapsed else None,
                "mean": round(sum(elapsed) / len(elapsed), 3) if elapsed else None,
            },
            "samples": rows[:3],
        }
    else:
        body = _client_ping(args.host, args.port, args.shard_index, args.payload_kb)

    manifest = {
        "schema": "nextgen_clean_slate_cpu_p1_shard_manifest_v1",
        "research_only": True,
        "aux_server_command": (
            f"py scripts/run_nextgen_clean_slate_cpu_p1_shard_ping_v1.py "
            f"--mode server --port {args.port}"
        ),
        "primary_client_command": (
            f"py scripts/run_nextgen_clean_slate_cpu_p1_shard_ping_v1.py "
            f"--mode client --host AUX_IP --port {args.port} "
            f"--shard-index 1 --payload-kb {args.payload_kb}"
        ),
        "note": "Same pattern as comp_en_tech_poc_aux_pc_manifest; merge not required for P1",
    }

    doc = {
        "schema": "nextgen_clean_slate_cpu_p1_shard_ping_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "mode": args.mode,
        "measurement": body,
        "manifest": manifest,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"wrote": str(args.out_json), "mode": args.mode}, ensure_ascii=False))
    if args.mode == "client":
        m = body if isinstance(body, dict) else {}
        if int(m.get("rounds_ok") or 0) < 1:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
