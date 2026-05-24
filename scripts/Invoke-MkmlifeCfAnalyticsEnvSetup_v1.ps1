#Requires -Version 5.1
<#
.SYNOPSIS
  Wire MKM_MKMLIFE_CF_ANALYTICS_TOKEN in .env (from CLOUDFLARE_API_TOKEN if unset), sync User env, run CF probe + Phase4.
.NOTES
  Does not print secret values. mkmlife zone needs Zone Read + Analytics Read on that zone (not jemaai-only).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$SkipProbe,
    [switch]$SkipSync,
    [switch]$SkipTaskRegister
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$envFile = Join-Path $WorkspaceRoot ".env"
if (-not (Test-Path -LiteralPath $envFile)) {
    throw "Missing .env: $envFile"
}

$py = if (Test-Path "$env:WINDIR\py.exe") { "$env:WINDIR\py.exe" } else { "py" }
$sync = Join-Path $WorkspaceRoot "projects\bitcoin-trading\ops\windows-rehearsal\sync_required_env_to_user.ps1"

& $py -c @"
from pathlib import Path
root = Path(r'$WorkspaceRoot')
env = root / '.env'
lines = env.read_text(encoding='utf-8').splitlines()
keys = {}
order = []
for line in lines:
    s = line.strip()
    if not s or s.startswith('#') or '=' not in s:
        continue
    k, v = line.split('=', 1)
    k = k.strip()
    keys[k] = v
    if k not in order:
        order.append(k)

cf = (keys.get('CLOUDFLARE_API_TOKEN') or keys.get('CF_API_TOKEN') or '').strip().strip('\"').strip(\"'\")
mk = (keys.get('MKM_MKMLIFE_CF_ANALYTICS_TOKEN') or '').strip().strip('\"').strip(\"'\")
changed = False
if cf and not mk:
    keys['MKM_MKMLIFE_CF_ANALYTICS_TOKEN'] = cf
    if 'MKM_MKMLIFE_CF_ANALYTICS_TOKEN' not in order:
        order.append('MKM_MKMLIFE_CF_ANALYTICS_TOKEN')
    changed = True

out = []
seen = set()
for line in lines:
    s = line.strip()
    if s.startswith('#') or '=' not in s or not s:
        out.append(line)
        continue
    k = line.split('=', 1)[0].strip()
    if k in keys and k not in seen:
        out.append(f'{k}={keys[k]}')
        seen.add(k)
    elif k not in keys:
        out.append(line)

for k in order:
    if k not in seen and k in keys:
        out.append(f'{k}={keys[k]}')
        seen.add(k)

if changed:
    env.write_text('\n'.join(out) + ('\n' if out else ''), encoding='utf-8')
print('MKM_MKMLIFE_CF_ANALYTICS_TOKEN wired_from_cloudflare=' + str(changed))
print('mkmlife_token_configured=' + str(bool((keys.get('MKM_MKMLIFE_CF_ANALYTICS_TOKEN') or cf).strip())))
"@

if (-not $SkipSync) {
    if (-not (Test-Path -LiteralPath $sync)) {
        throw "Missing sync script: $sync"
    }
    Write-Host "==> sync User env (CLOUDFLARE + MKM_MKMLIFE_CF_ANALYTICS_TOKEN)" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File $sync
}

if (-not $SkipTaskRegister) {
    $tasks = @(
        @{ Script = "Register-Op30MagicOrbEnvelopeDailyTask.ps1"; Name = "MKM_Op30_MagicOrb_Envelope_Daily" },
        @{ Script = "Register-Op30MagicOrbTrafficWeeklyTask.ps1"; Name = "MKM_Op30_MagicOrb_Traffic_Weekly" }
    )
    foreach ($t in $tasks) {
        $p = Join-Path $WorkspaceRoot "scripts\$($t.Script)"
        if (Test-Path -LiteralPath $p) {
            Write-Host "==> register $($t.Name)" -ForegroundColor Cyan
            & powershell -NoProfile -ExecutionPolicy Bypass -File $p
        }
    }
}

if (-not $SkipProbe) {
    Write-Host "==> CF probe + Phase4 observability" -ForegroundColor Cyan
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $WorkspaceRoot "scripts\Invoke-Op30Phase4TrafficObservability_v1.ps1")
}

$probePath = Join-Path $WorkspaceRoot "reports\mkmlife_cf_traffic_probe_latest.json"
if (Test-Path -LiteralPath $probePath) {
    $p = Get-Content -LiteralPath $probePath -Raw -Encoding UTF8 | ConvertFrom-Json
    Write-Host ("CF probe: token_present={0} zone_read_ok={1} fetched={2} source={3}" -f `
        $p.token_present, $p.zone_read_ok, $p.cf_analytics_fetched, $p.token_source_env)
    if (-not $p.zone_read_ok) {
        Write-Host @"

[ACTION] Cloudflare dashboard → My Profile → API Tokens → Create token
  - Permissions: Zone / Zone Read + Zone / Analytics Read (mkmlife.com zone)
  - mkmlife only: Zone Read + Analytics on mkmlife.com (NOT jemaai rulesets).
  - jemaai edge: CLOUDFLARE_RULESETS_API_TOKEN — py scripts/check_cloudflare_token_roles_v1.py
  - Do NOT create a new CLOUDFLARE_API_TOKEN for mkmlife when jemaai apply fails (separate roles).
  - Re-run: powershell -File scripts\Invoke-MkmlifeCfAnalyticsEnvSetup_v1.ps1

"@ -ForegroundColor Yellow
    }
}
