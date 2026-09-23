# MKM Secure Agent Runtime V0.4

Bounded local-first runtime candidate for MKM's Desktop Commander-class tool layer.

## Implemented

### V0 core
- approved-root path policy
- list/read/write file primitives
- HUMAN_GATE on writes and command execution
- argv-only subprocess execution; never `shell=True`
- executable allowlist + blocked risky Git subcommands
- SHA-256 Thin Coordinates
- append-only JSONL action receipts without raw file/prompt contents
- semantic state remains `NOT_ADJUDICATED`; SEND remains `HOLD`

### V0.1 MCP
- MCP Python SDK v2 stdio server
- tool discovery / structured schemas
- out-of-band local approval broker
- approval state must live outside model-accessible roots
- approval records store action metadata + digest, not raw content
- one-time exact-action approval consumption
- local approval CLI

### V0.2 privacy gate
- deterministic local secret / direct-identifier prefilter
- automatic scan before local file body is released through MCP
- SECRET -> DENY
- direct identifier + medical context -> PHI / HOLD
- PERSONAL -> HOLD
- metadata-only local file privacy scan tool
- person-name detection remains NOT_ESTABLISHED

### V0.3 secret broker
- Windows current-user DPAPI secret-at-rest store
- local-only secret management CLI
- MCP exposes secret-handle metadata only
- no MCP tool can return decrypted secret material
- decrypted material API exists only for future trusted local consumers
- best-effort bytearray wipe after local verification

## Exposed MCP tools

- `runtime_status`
- `list_directory`
- `secret_handle_info`
- `read_text_file`
- `privacy_scan_file`
- `thin_coordinate`
- `request_write_text`
- `execute_write_text`
- `request_command`
- `execute_command`
- `ollama_health`
- `ollama_generate`

### V0.4 rollback
- approved text writes capture a Windows DPAPI-encrypted pre-write snapshot
- existing files restore original bytes
- newly created files can be removed by rollback
- rollback is local CLI only; no MCP restore tool
- write_text is bounded to 1 MiB in V0.4

## Explicitly not implemented

- browser/GUI automation
- secret injection into browser/subprocess
- remote relay/device pairing
- delete/move/destructive tools
- git push/deploy/SEND
- PHI production workflow
- reliable person-name recognition
- independent security review

## Current validation

- full targeted suite on Windows: 44 PASS
- MCP stdio wire negotiation: protocol 2026-07-28 observed
- approval round trip: PASS in synthetic fixture
- privacy body blocking on wire: PASS
- DPAPI secret metadata-only wire smoke: PASS
- write -> encrypted snapshot -> local rollback wire smoke: PASS
- Ollama executable installed on tested PC, but running local Ollama instance was not established at probe time

## Evidence ceiling

`BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_4_CANDIDATE`

This is a development candidate, not a deployment or production-security authorization.
