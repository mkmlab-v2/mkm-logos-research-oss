# Security Policy

## Supported versions

| Version | Supported |
| ------- | --------- |
| `main` (solo OSS subset) | Yes |

This repository is **research and developer tooling** — not a hosted SaaS with SLAs.

## Reporting a vulnerability

If you believe you found a security issue in **published** MKM OSS code:

1. **Do not** open a public GitHub issue with exploit details or live secrets.
2. Use [GitHub Security Advisories](https://github.com/mkmlab-v2/mkm-universal-root/security/advisories/new) (preferred) or email the maintainer with: affected path, reproduction steps, impact, and your contact.
3. Allow reasonable time for triage before public disclosure.

For accidental secret commits: rotate the credential immediately — scanning cannot un-leak a key.

## Secret hygiene (operators)

Before fork or public push, from repo root:

```bash
python3 scripts/check_mkm_secret_patterns_v1.py
python3 scripts/check_hardcoded_workspace_paths_v1.py --scope oss --strict
python3 scripts/run_universal_root_oss_cursor_smoke_v1.py
```

Windows: use `py` instead of `python3`.

Never commit:

- `.env`, API keys, bearer tokens, exchange credentials
- Patient, grant, or trading-approval artifacts
- Local operator logs or machine-specific pointers

Use `.env.example` placeholders only. Store live secrets in your OS secret store — not in git.

## Automated scanning (in this repo)

| Tool | Role |
| ---- | ---- |
| `scripts/check_mkm_secret_patterns_v1.py` | High-confidence pattern scan (stdlib + git; no extra deps) |
| `scripts/check_hardcoded_workspace_paths_v1.py --scope oss --strict` | Launch Gate #1 — no hardcoded monorepo paths |
| `.github/workflows/oss-smoke.yml` | CI: path audit + smoke + contributor stub pytest |

Optional (maintainers): install `gitleaks` locally for deeper scans before push.

## Scope limits

- B-track `[HYPO]` outputs are **not** operational security controls.
- MIT license — no warranty. See [README.md](README.md) disclaimer.
- This OSS subset does **not** enable exchange execution or auto-promotion to production.

## Community FAQ (Show HN / GitHub discussions)

**Do you run a central server that ingests my code?**  
No MKM-hosted ingestion service ships in this repo. Smoke tests and benches run on your machine only.

**What leaves my machine?**  
Nothing required for the hero smoke path. Optional local SLM tiers are your choice and subject to **your** provider egress policies.

**Is 0.47% a global hallucination rate?**  
No. It is `english_only_distortion_rate` on a **500-pair closed fixture** (lexicon plane). See `reports/universal_root_oss_cursor_smoke_v1_latest.json` after smoke.

## Related docs (in this export)

- OSS release policy: `docs/final/artifacts/mkm_solo_oss_release_policy_v1_latest.json`
- Public GTM pointer (OSS-safe): `docs/final/artifacts/mkm_universal_root_public_gtm_pointer_v1.json`
- Contributor guide: `CONTRIBUTING.md`
