#!/usr/bin/env python3
"""RTT probe for nextgen clean-slate CPU sandbox (loopback, client, or server)."""
from __future__ import annotations

import argparse
import json
import socket
import statistics
import struct
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = (
    ROOT / "experiments/nextgen_clean_slate_cpu_v1/results/rtt_probe_v1_latest.json"
)


def _utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _percentile(values: list[float], pct: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    idx = int(round((pct / 100.0) * (len(ordered) - 1)))
    return ordered[max(0, min(idx, len(ordered) - 1))]


def _serve(port: int) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", port))
    sock.listen(5)
    print(f"[server] listening 0.0.0.0:{port}", flush=True)
    try:
        while True:
            conn, addr = sock.accept()
            with conn:
                hdr = _recv_exact(conn, 4)
                if not hdr:
                    continue
                (length,) = struct.unpack("!I", hdr)
                payload = _recv_exact(conn, length)
                if payload is None:
                    continue
                conn.sendall(hdr + payload)
                print(f"[server] echoed {length} bytes from {addr[0]}", flush=True)
    except KeyboardInterrupt:
        print("[server] stopped", flush=True)
        return 0
    finally:
        sock.close()


def _recv_exact(conn: socket.socket, n: int) -> bytes | None:
    buf = bytearray()
    while len(buf) < n:
        chunk = conn.recv(n - len(buf))
        if not chunk:
            return None
        buf.extend(chunk)
    return bytes(buf)


def _client_roundtrip(host: str, port: int, payload: bytes) -> float:
    start = time.perf_counter()
    with socket.create_connection((host, port), timeout=30.0) as conn:
        hdr = struct.pack("!I", len(payload))
        conn.sendall(hdr + payload)
        back_hdr = _recv_exact(conn, 4)
        if not back_hdr:
            raise RuntimeError("empty header")
        (length,) = struct.unpack("!I", back_hdr)
        back = _recv_exact(conn, length)
        if back != payload:
            raise RuntimeError("payload mismatch")
    return (time.perf_counter() - start) * 1000.0


def _run_client(
    host: str,
    port: int,
    rounds: int,
    payload_kb: int,
) -> dict[str, Any]:
    payload = bytes(payload_kb * 1024)
    samples: list[float] = []
    errors = 0
    for i in range(rounds):
        try:
            samples.append(_client_roundtrip(host, port, payload))
        except OSError as exc:
            errors += 1
            if errors > 3 and not samples:
                raise RuntimeError(f"RTT client failed: {exc}") from exc
    return {
        "host": host,
        "port": port,
        "payload_kb": payload_kb,
        "rounds_requested": rounds,
        "rounds_ok": len(samples),
        "errors": errors,
        "rtt_ms": {
            "min": round(min(samples), 3) if samples else None,
            "p50": round(statistics.median(samples), 3) if samples else None,
            "p95": round(_percentile(samples, 95), 3) if samples else None,
            "p99": round(_percentile(samples, 99), 3) if samples else None,
            "max": round(max(samples), 3) if samples else None,
            "mean": round(statistics.mean(samples), 3) if samples else None,
        },
    }


def _loopback(port: int, rounds: int, payload_kb_grid: list[int]) -> dict[str, Any]:
    import threading

    ready = threading.Event()
    stop = threading.Event()
    err: list[BaseException] = []

    def _runner() -> None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.settimeout(1.0)
            sock.bind(("127.0.0.1", port))
            sock.listen(128)
            ready.set()
            while not stop.is_set():
                try:
                    conn, _ = sock.accept()
                except socket.timeout:
                    continue
                with conn:
                    hdr = _recv_exact(conn, 4)
                    if not hdr:
                        continue
                    (length,) = struct.unpack("!I", hdr)
                    payload = _recv_exact(conn, length)
                    if payload is None:
                        continue
                    conn.sendall(hdr + payload)
            sock.close()
        except BaseException as exc:  # noqa: BLE001
            err.append(exc)

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    if not ready.wait(timeout=5.0):
        raise RuntimeError("loopback server did not start")
    time.sleep(0.05)
    rows = []
    for kb in payload_kb_grid:
        rows.append(_run_client("127.0.0.1", port, rounds, kb))
    stop.set()
    t.join(timeout=3.0)
    if err:
        raise err[0]
    return {"mode": "loopback", "host": "127.0.0.1", "port": port, "grid": rows}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--mode",
        choices=["server", "client", "loopback"],
        default="loopback",
    )
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=19876)
    ap.add_argument("--rounds", type=int, default=20)
    ap.add_argument("--payload-kb", type=int, default=256)
    ap.add_argument(
        "--payload-kb-grid",
        default="64,256,1024",
        help="Comma-separated KB sizes (loopback mode)",
    )
    ap.add_argument("--out-json", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    if args.mode == "server":
        return _serve(args.port)

    if args.mode == "loopback":
        grid = [int(x.strip()) for x in args.payload_kb_grid.split(",") if x.strip()]
        body = _loopback(args.port, args.rounds, grid)
    else:
        body = _run_client(args.host, args.port, args.rounds, args.payload_kb)

    doc = {
        "schema": "nextgen_clean_slate_cpu_rtt_probe_v1",
        "generated_at_utc": _utc(),
        "research_only": True,
        "mode": args.mode,
        "measurement": body,
    }
    args.out_json.parent.mkdir(parents=True, exist_ok=True)
    args.out_json.write_text(
        json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps({"wrote": str(args.out_json), "mode": args.mode}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
