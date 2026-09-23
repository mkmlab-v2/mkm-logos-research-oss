# MKM Secure Agent Runtime V0

Bounded local-first runtime candidate for MKM's Desktop Commander-class tool layer.

## Implemented in V0

- approved-root path policy
- list/read/write file primitives
- HUMAN_GATE on writes and command execution
- argv-only subprocess execution; never `shell=True`
- read-only-ish executable allowlist with blocked risky Git subcommands
- local-loopback-only Ollama gateway
- PHI HOLD by default; SECRET denied to model
- opaque `secret://...` handles; no secret storage/resolution
- SHA-256 Thin Coordinates
- append-only JSONL receipts without raw file/prompt contents
- semantic state always `NOT_ADJUDICATED`; SEND always `HOLD`

## Explicitly not implemented

- OS password vault integration
- credential material retrieval
- browser/GUI automation
- remote relay/device pairing
- delete/move/destructive tools
- git push/deploy/SEND
- PHI production workflow
- full MCP transport/server

## Evidence ceiling

`BOUNDED_LOCAL_RUNTIME_CANDIDATE`

This V0 is a program component, not a deployment authorization.
