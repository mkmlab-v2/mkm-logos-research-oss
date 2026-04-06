# AI Triage Report (Latest)

- task: \Bitcoin-Ops-Phase1-Chain-Daily
- generated_utc: 2026-04-06T12:19:18.6242896+00:00
- mode: read-only analysis
## Findings
Cursor CLI agent invocation returned no text output in non-interactive mode.

## Root causes (ranked)
1. This host resolves cursor but not standalone agent, and cursor agent -p ... appears to run without structured stdout.
2. Non-interactive prompt mode may require different CLI flags/version than currently installed (Cursor 3.0.9).
3. Ops evidence bundle was generated successfully, so only the AI handoff leg is degraded.

## Immediate mitigations (no code)
- Keep generating ai_triage_bundle_latest.md each run as a deterministic evidence packet.
- Run manual triage in current chat by attaching that bundle when needed.
- Validate supported non-interactive flags for cursor agent on this machine.

## Minimal code fixes (optional)
- Install/enable a CLI variant that supports agent -p ... --output-format text in terminal mode.
- Once confirmed, replace the fallback path with that exact command.

## Go/No-Go
GO for evidence capture automation, NO_GO for fully automated AI triage output until CLI output mode is confirmed.
