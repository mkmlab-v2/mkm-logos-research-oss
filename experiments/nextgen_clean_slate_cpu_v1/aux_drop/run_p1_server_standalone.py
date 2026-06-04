#!/usr/bin/env python3
"""P1 shard digest server for aux PC (no repo import). Copy to Z:\\nextgen_cpu_aux\\."""
from __future__ import annotations

import argparse
import hashlib
import socket
import struct
import sys


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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=19877)
    args = ap.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", args.port))
    sock.listen(128)
    print(f"[aux-p1-server] 0.0.0.0:{args.port} (Ctrl+C stop)", flush=True)
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
                conn.sendall(_digest_shard(shard_index, payload))
                print(
                    f"[aux-p1-server] shard={shard_index} bytes={length} from {addr[0]}",
                    flush=True,
                )
    except KeyboardInterrupt:
        print("[aux-p1-server] stopped", flush=True)
        return 0
    finally:
        sock.close()


if __name__ == "__main__":
    raise SystemExit(main())
