# mkmlab.space parallel readiness: local probe + VPS sync dry-run + CF DNS ensure (optional).
param(
    [switch]$SkipCloudflare,
    [switch]$ApplyCloudflare,
    [switch]$TryVpsSync,
    [string]$OriginIp = "148.230.97.246"
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$out = Join-Path $root "reports\mkmlab_space_deploy_readiness_latest.json"

$steps = [System.Collections.Generic.List[object]]::new()

function Add-Step($name, $code, $note) {
    $steps.Add([ordered]@{ step = $name; exit_code = $code; note = $note }) | Out-Null
}

& py (Join-Path $root "scripts\probe_mkmlab_space_readiness_v1.py")
Add-Step "probe_mkmlab_space_readiness_v1" $LASTEXITCODE "local+http"

if (-not $SkipCloudflare) {
    $zid = "38a47f29983bd4ebce3798be08f59ba3"
    $cfArgs = @(
        "scripts\ensure_mkmlab_space_cloudflare_dns_v1.py",
        "--origin-ip", $OriginIp,
        "--zone-id", $zid
    )
    if (-not $ApplyCloudflare) { $cfArgs += "--what-if" }
    & py @cfArgs
    Add-Step "ensure_mkmlab_space_cloudflare_dns_v1" $LASTEXITCODE $(if ($ApplyCloudflare) { "applied" } else { "what-if" })
}

if ($TryVpsSync) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1")
    Add-Step "Sync-MkmlabRedesignToVps_v1" $LASTEXITCODE "scp"
} else {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1") -DryRun
    Add-Step "Sync-MkmlabRedesignToVps_v1_dryrun" $LASTEXITCODE "plan only"
}

$worst = ($steps | ForEach-Object { $_.exit_code } | Measure-Object -Maximum).Maximum
if ($null -eq $worst) { $worst = 0 }

$payload = [ordered]@{
    schema           = "mkmlab_space_deploy_readiness_v1"
    generated_at_utc = (Get-Date).ToUniversalTime().ToString("o")
    infra            = "Hostinger VPS + Cloudflare (not hPanel public_html)"
    origin_ip        = $OriginIp
    steps            = @($steps)
    worst_exit       = [int]$worst
    nginx_on_vps     = "scripts/deploy/linux/apply_mkmlab_space_nginx_v1.sh -y"
}
$dir = Split-Path $out -Parent
if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
($payload | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $out -Encoding UTF8
Write-Host "Wrote $out worst_exit=$worst"
exit $worst
