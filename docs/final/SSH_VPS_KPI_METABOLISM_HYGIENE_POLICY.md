# SSH VPS KPI Metabolism Hygiene Policy

## Purpose

Keep the VPS `append -> export` cron chain stable while preventing Git workspace drift from runtime artifacts.

## Scope

- VPS repo: `/opt/mkm-lab-workspace-v2`
- Runtime source log: `/root/.pm2/logs/bitcoin-live-error.log`
- Derived outputs:
  - `docs/final/artifacts/derived/kpi_metabolism_cron.log`
  - `docs/final/artifacts/derived/log_metabolism_from_kpi_vps_export_v1.jsonl`
  - `docs/final/artifacts/derived/vps_kpi_metabolism_export_report_v1.json`

## Policy

1. **Git hygiene first**
   - Treat derived runtime outputs as non-source files.
   - Keep code/config tracked, keep runtime artifacts ignored.
   - Never run destructive Git commands on VPS (`reset --hard`, `clean -fd`) for routine sync.

2. **Pull safety gate**
   - Always run `git fetch` + `git status -sb` before pull.
   - If dirty, use `git stash push -u` with timestamp label.
   - Pull with `git pull --ff-only origin main` only.

3. **Rollover and retention**
   - Rotate `log_metabolism_from_kpi_vps_export_v1.jsonl` into timestamped archive files.
   - Compress rollover files (`.gz`) and keep 14 days by default.
   - Keep active JSONL small to reduce diff noise and recovery time.

4. **Cron continuity**
   - Keep current 5-minute chain (`append -> export`) unchanged unless incident response requires edits.
   - Preserve `MKM_KPI_PROXY_LOG=/root/.pm2/logs/bitcoin-live-error.log` as the operational value.

5. **Validation contract**
   - Health is confirmed only when:
     - `kpi_metabolism_cron.log` shows recent successful cycles
     - `vps_kpi_metabolism_export_report_v1.json` has `ok: true`
     - `output_line_count` and JSONL `wc -l` increase together

## Recommended `.gitignore` entries

```gitignore
# VPS runtime artifacts (kpi metabolism)
docs/final/artifacts/derived/kpi_metabolism_cron.log
docs/final/artifacts/derived/log_metabolism_from_kpi_vps_export_v1.jsonl
docs/final/artifacts/derived/vps_kpi_metabolism_export_report_v1.json
docs/final/artifacts/derived/rollover/
```

## Operator Runbook (copy/paste)

```bash
set -e
cd /opt/mkm-lab-workspace-v2

# 1) Pre-pull safety
git fetch origin
git status -sb
if [ -n "$(git status --porcelain)" ]; then
  git stash push -u -m "pre-pull-safety-$(date -u +%Y%m%dT%H%M%SZ)"
fi
git pull --ff-only origin main

# 2) Rollover
mkdir -p docs/final/artifacts/derived/rollover
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
SRC="docs/final/artifacts/derived/log_metabolism_from_kpi_vps_export_v1.jsonl"
DST="docs/final/artifacts/derived/rollover/log_metabolism_from_kpi_vps_export_v1_${STAMP}.jsonl"
if [ -f "$SRC" ] && [ -s "$SRC" ]; then
  cp "$SRC" "$DST"
  : > "$SRC"
  gzip -f "$DST"
fi

# 3) Retention (14 days)
find docs/final/artifacts/derived/rollover -type f -name "*.gz" -mtime +14 -delete

# 4) Health check
tail -n 50 docs/final/artifacts/derived/kpi_metabolism_cron.log || true
wc -l docs/final/artifacts/derived/log_metabolism_from_kpi_vps_export_v1.jsonl
cat docs/final/artifacts/derived/vps_kpi_metabolism_export_report_v1.json
```
