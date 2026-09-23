# MKM Secure Agent Runtime V1.0

Bounded local-first development candidate for MKM's Desktop Commander-class runtime.

## Layer history

- V0: approved-root file/command primitives, Thin Coordinates, receipts
- V0.1: MCP stdio + exact one-time out-of-band HUMAN_GATE
- V0.2: deterministic privacy prefilter
- V0.3: Windows current-user DPAPI secret store
- V0.4: DPAPI-encrypted rollback snapshots
- V0.5: Windows tray approval UI + loopback-only Ollama manager
- V0.6: isolated Windows UIA Desktop Action Layer
- V0.7: process/class based App Adapter Layer
- V0.8: semantic Developer Adapter for VS Code/Cursor
- V0.9: dedicated Cursor Worker Session binding
- V1.0: fail-closed Cursor Agent desktop-bridge worker layer

## V1.0 Cursor Agent Worker

V1.0 does **not** blindly type prompts into arbitrary Cursor windows.

It uses Cursor's own desktop bridge CLI only when all of these are true:

1. the V0.9 developer session is freshly `BOUND_ESTABLISHED`
2. exactly one live desktop-bridge discovery record exists for that exact session `userDataDir`
3. the target thread appears in that exact bridge instance
4. the prompt passes local privacy and forbidden-action policy
5. an out-of-band local HUMAN_GATE approval matches the exact:
   - session id
   - bound window pid
   - workspace path
   - thread id
   - prompt SHA-256
   - prompt length
   - force=false

If any bridge condition is missing, prompt submission fails closed.

## Cursor desktop bridge facts observed from the installed Cursor 3.17.19 code

The installed CLI contains a hidden desktop bridge command surface with:

- `cursor desktop ls`
- `cursor desktop send <thread> [text...]`
- `--json`
- `--stdin`
- `--force`

The implementation internally supports:
- discovery records with `protocolVersion`, `pid`, `socketPath`, `token`, `appName`, `appVersion`, `userDataDir`
- `listThreads`
- `sendMessage`
- thread metadata including id, title, source, status, lastUpdatedAt and windowId

V1.0 intentionally disables force-send.

## V1.0 MCP tools

- `cursor_agent_status`
- `cursor_agent_threads`
- `request_cursor_agent_prompt`
- `execute_cursor_agent_prompt`

Prompt plaintext is not stored in approval metadata; approval binds to prompt hash + length.

Thread titles are passed through the local privacy scanner before release.

## Prompt policy

DENY:
- SECRET / PERSONAL / PHI-like prompt text
- force-send
- `git push`
- deploy / publish
- external send/email directives
- transfer / banking directives
- destructive directives such as delete-all / rm -rf
- extension install/uninstall directives

Allowed candidate prompts still require HUMAN_GATE.

## Live test PC state

### FACT

- Cursor installed version observed: 3.17.19
- V0.9 dedicated synthetic Cursor worker session can reach `BOUND_ESTABLISHED`
- installed Cursor source contains desktop-bridge client/server protocol code
- default discovery directory checked:
  `%USERPROFILE%\.cursor\desktop-bridge`
- live discovery directory was **not present**
- a V0.9 dedicated session using `--disable-extensions` also produced no discovery
- a separate probe using:
  - unique user-data-dir
  - empty extensions-dir
  - built-in extensions enabled
  also produced no discovery
- `cursor agent` invoked non-interactively exited 0 with no usable output
- a shared-login `--profile` / `--new-window` probe did not yield a unique binding marker
- no live Cursor Agent prompt was submitted by V1.0

### Current live state

`CURSOR_DESKTOP_BRIDGE_NOT_ESTABLISHED`

Therefore actual autonomous Cursor Agent prompting is **NOT_ESTABLISHED** on this PC.

## V1.0 synthetic validation

V1.0 targeted bridge tests: **9 PASS**

Validated:
- exact session bridge status
- sensitive thread-title redaction
- request does not send before approval
- approved exact prompt sends once
- changed prompt cannot reuse approval
- session-external thread is denied
- PERSONAL prompt is denied
- git-push directive is denied
- absent discovery fails closed

## Full regression state

A full V0-V1.0 regression was run after V1.0 integration.

Observed:

- **95 PASS**
- **1 FAIL**

Fresh failure:

`test_mcp_set_text_round_trip_and_exact_approval`

Expected:
`fixture-value`

Observed:
`..fixture-value`

This occurred in the existing V0.6 synthetic UI Edit path.

Current interpretation:

- fresh regression failure = FACT
- root cause = NOT_ADJUDICATED
- V1.0 bridge causality = NOT_ESTABLISHED
- full branch regression = FAIL

No automatic patch or second fresh rerun was used to erase this result.

## Evidence ceiling

`BOUNDED_CURSOR_AGENT_WORKER_V1_0_BRIDGE_GATED_CANDIDATE_WITH_REGRESSION_FAIL`

### SUPPORTED

- fail-closed exact-session bridge architecture
- exact prompt approval binding
- synthetic agent-bridge control logic

### NOT_ESTABLISHED

- live Cursor Agent prompt submission
- live Cursor-generated code editing
- bridge enablement mechanism on this installation
- V0.6 Edit regression root cause
- cross-project reliability
- production safety
- independent security review

### HOLD / NOT AUTHORIZED

- live Agent SEND while bridge is absent
- git push / deploy / SEND
- secret injection
- EMR/PHI production use
- merge / deployment
