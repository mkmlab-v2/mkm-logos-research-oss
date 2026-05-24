# One-shot mkmlab.space go-live: CF zone (create if missing) -> DNS A -> VPS sync -> probe.
# Infra: Hostinger VPS + Cloudflare only (not hPanel public_html).
param(
    [string]$AccountId = "646e42cf881ab43043c32430e99d9af4",
    [string]$OriginIp = "148.230.97.246",
    [switch]$SkipVpsSync,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$report = Join-Path $root "reports\mkmlab_space_golive_auto_latest.json"
$steps = [System.Collections.Generic.List[object]]::new()

function Step($n, $code, $detail) {
    $steps.Add([ordered]@{ step = $n; exit_code = [int]$code; detail = $detail }) | Out-Null
}

# 1) Cloudflare zone
$zoneCreate = Join-Path $PSScriptRoot "Invoke-CloudflareZoneCreate_v1.ps1"
$zcArgs = @(
    "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $zoneCreate,
    "-AccountId", $AccountId, "-ZoneName", "mkmlab.space",
    "-OutJson", (Join-Path $root "reports\cloudflare_zone_create_mkmlab_space_latest.json")
)
if ($WhatIfOnly) { $zcArgs += "-WhatIf" }
& powershell @zcArgs
Step "cloudflare_zone_create" $LASTEXITCODE "mkmlab.space"

# 2) DNS A + www CNAME (needs zone visible to token)
if (-not $WhatIfOnly) {
    $zid = "38a47f29983bd4ebce3798be08f59ba3"
    & py (Join-Path $root "scripts\ensure_mkmlab_space_cloudflare_dns_v1.py") --origin-ip $OriginIp --zone-id $zid
    Step "cloudflare_dns_ensure" $LASTEXITCODE "apex A proxied"
    & py (Join-Path $root "scripts\set_hostinger_mkmlab_nameservers_v1.py")
    Step "hostinger_registrar_ns" $LASTEXITCODE "Cloudflare NS at Hostinger"
    & py (Join-Path $root "scripts\prune_mkmlab_cloudflare_dns_v1.py")
    Step "cloudflare_dns_prune" $LASTEXITCODE "stray A / AAAA"
}

# 3) VPS static (idempotent)
if (-not $SkipVpsSync -and -not $WhatIfOnly) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1")
    Step "vps_scp" $LASTEXITCODE "/var/www/mkmlab"
    $ngx = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\jemaai-cloud-mvp\nginx_mkmlab_space.conf.example"
    $vpsHost = [Environment]::GetEnvironmentVariable("MKM_VPS_HOST", "User")
    if ([string]::IsNullOrWhiteSpace($vpsHost)) { $vpsHost = "srv1101456.hstgr.cloud" }
    $user = [Environment]::GetEnvironmentVariable("MKM_VPS_USER", "User")
    if ([string]::IsNullOrWhiteSpace($user)) { $user = "root" }
    $extra = [Environment]::GetEnvironmentVariable("MKM_VPS_SCP_EXTRA_ARGS", "User")
    $sshTarget = "${user}@${vpsHost}"
    if (-not [string]::IsNullOrWhiteSpace($extra)) {
        & scp @($extra.Split(" ", [StringSplitOptions]::RemoveEmptyEntries)) $ngx "${sshTarget}:/etc/nginx/sites-available/mkmlab.space"
    } else {
        & scp $ngx "${sshTarget}:/etc/nginx/sites-available/mkmlab.space"
    }
    if ($LASTEXITCODE -eq 0) {
        $reloadCmd = "ln -sf /etc/nginx/sites-available/mkmlab.space /etc/nginx/sites-enabled/mkmlab.space && nginx -t && systemctl reload nginx"
        if (-not [string]::IsNullOrWhiteSpace($extra)) {
            & ssh @($extra.Split(" ", [StringSplitOptions]::RemoveEmptyEntries)) $sshTarget $reloadCmd
        } else {
            & ssh $sshTarget $reloadCmd
        }
        Step "vps_nginx" $LASTEXITCODE "reload"
    } else {
        Step "vps_nginx" 1 "scp nginx failed"
    }
}

# 4) Probe
if (-not $WhatIfOnly) {
    & py (Join-Path $root "scripts\probe_mkmlab_space_readiness_v1.py")
    Step "probe" $LASTEXITCODE "public http"
}

$worst = ($steps | ForEach-Object { $_.exit_code } | Measure-Object -Maximum).Maximum
$zcJson = Join-Path $root "reports\cloudflare_zone_create_mkmlab_space_latest.json"
$ns = @()
if (Test-Path $zcJson) {
    $z = Get-Content $zcJson -Raw | ConvertFrom-Json
    if ($z.name_servers) { $ns = @($z.name_servers) }
}

$payload = [ordered]@{
    schema           = "mkmlab_space_golive_auto_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    worst_exit       = [int]$worst
    steps            = @($steps)
    cloudflare_name_servers = $ns
    manual_if_still_403 = "If probe still hcdn 403: set registrar NS to cloudflare_name_servers (Hostinger Domains -> mkmlab.space -> Nameservers). API cannot change Hostinger NS without hPanel API token."
    rerun_dns         = "py scripts/ensure_mkmlab_space_cloudflare_dns_v1.py --origin-ip $OriginIp"
}
($payload | ConvertTo-Json -Depth 8) | Set-Content -LiteralPath $report -Encoding UTF8
Write-Host "Wrote $report worst_exit=$worst"
if ($ns.Count -gt 0) {
    Write-Host "Cloudflare NS (registrar):" -ForegroundColor Cyan
    $ns | ForEach-Object { Write-Host "  $_" }
}
exit $worst
