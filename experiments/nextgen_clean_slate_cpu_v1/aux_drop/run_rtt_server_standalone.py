#!/usr/bin/env python3
"""Standalone RTT echo server for aux PC (no repo import). Copy to Z:\\nextgen_cpu_aux\\."""
from __future__ import annotations

import argparse
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


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=19876)
    args = ap.parse_args()
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", args.port))
    sock.listen(128)
    print(f"[aux-rtt-server] 0.0.0.0:{args.port} (Ctrl+C stop)", flush=True)
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
                print(f"[aux-rtt-server] echo {length} from {addr[0]}", flush=True)
    except KeyboardInterrupt:
        return 0
    finally:
        sock.close()


if __name__ == "__main__":
    raise SystemExit(main())
