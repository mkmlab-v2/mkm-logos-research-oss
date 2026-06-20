# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| `main` (solo OSS subset) | Yes |

This repository is **research and developer tooling** — not a hosted SaaS with SLAs.

## Reporting a vulnerability

If you believe you found a security issue in **published** MKM OSS code:

1. **Do not** open a public GitHub issue with exploit details or live secrets.
2. Email the maintainer with: affected path, reproduction steps, impact, and your contact.
3. Allow reasonable time for triage before public disclosure.

For accidental secret commits: rotate the credential immediately — scanning cannot un-leak a key.

## Secret hygiene (operators)

Before fork or public push:

```powershell
cd C:\workspace
py scripts/check_mkm_secret_patterns_v1.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/run_mkm_secret_scan_v1.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/Verify-GitWorkspaceSanity.ps1
pre-commit run --all-files   # optional, after: pre-commit install
```

Never commit:

- `.env`, API keys, DPAPI exports, exchange credentials
- Local `MISSION_LOG.md`, machine-specific pointers
- Patient, grant, or trading-approval artifacts

Use `.env.example` placeholders only. Store live secrets via DPAPI (`scripts/security_agent_manager.py`) or your OS secret store — not in git.

## Automated scanning

| Tool | Role |
| ---- | ---- |
| `scripts/check_mkm_secret_patterns_v1.py` | High-confidence pattern scan (always runnable) |
| `gitleaks` + `.gitleaks.toml` | Optional deeper scan when binary is installed |
| `.pre-commit-config.yaml` | Local hook: gitleaks + pattern scan on `git commit` |

Install hooks:

```powershell
pre-commit install
```

## Scope limits

- B-track `[HYPO]` outputs are **not** operational security controls.
- MIT license — no warranty. See [README.md](README.md) disclaimer.
- **Track A live trading** remains LOCKED in this workspace; OSS does not enable exchange execution by default.

## Related docs

- Public copy checklist: `docs/final/PUBLIC_FACING_SECURITY_AND_IP_COPY_CHECKLIST_V1.md`
- OSS release policy: `docs/final/artifacts/mkm_solo_oss_release_policy_v1_latest.json`
- Hybrid AI related work (B-track): `docs/research/NEXT_GEN_HYBRID_AI_MKM_MERGED_LIT_REVIEW_2026-06-20.md`
