# MKM Secure Agent Runtime V0.5

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
- approval state outside model-accessible roots
- approval records store action metadata + digest, not raw content
- one-time exact-action approval consumption
- local approval CLI

### V0.2 privacy gate
- deterministic local secret/direct-identifier prefilter
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
- no MCP tool returns decrypted secret material
- best-effort bytearray wipe after trusted local verification

### V0.4 rollback
- approved text writes capture Windows DPAPI-encrypted pre-write snapshots
- existing files restore original bytes
- newly created files can be removed by rollback
- rollback is local CLI only; no MCP restore tool
- write_text bounded to 1 MiB

### V0.5 Windows tray / local approval UI
- pystray-based Windows notification-area shell
- approval window hidden by default
- new REQUESTED approval opens a local approval popup
- Approve once / Deny buttons call the local ApprovalBroker directly
- popup displays target + argument digest, not raw write contents
- headless TrayController separates approval logic from GUI
- OllamaManager probes only loopback 127.0.0.1:11434
- optional Ollama autostart forces OLLAMA_HOST=127.0.0.1:11434
- failed autostart cleans up processes started by MKM
- tray quit stops Ollama only when MKM started that process

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

## Explicitly not implemented

- browser/GUI automation of third-party apps
- secret injection into browser/subprocess
- remote relay/device pairing
- general delete/move tools
- git push/deploy/SEND
- PHI production workflow
- reliable person-name recognition
- independent security review
- production installer/autostart registration

## Current validation

- full targeted Windows suite: 52 PASS
- MCP stdio protocol observed: 2026-07-28
- approval request -> local approval -> exact one-time execution: PASS
- privacy body blocking on MCP wire: PASS
- DPAPI secret metadata-only wire smoke: PASS
- write -> encrypted snapshot -> local rollback: PASS
- actual Ollama auto-connect: PASS after V0.5 timeout/cleanup hardening
  - executable: installed
  - became healthy in 5.69s
  - 11 local models observed
  - process started by MKM was stopped after smoke
- Windows GUI smoke: PASS
  - new synthetic approval caused approval window to become visible
  - pending row displayed
  - Approve once button moved REQUESTED -> APPROVED

## Evidence ceiling

`BOUNDED_LOCAL_SECURE_AGENT_RUNTIME_V0_5_CANDIDATE`

This is a development candidate, not a deployment or production-security authorization.
