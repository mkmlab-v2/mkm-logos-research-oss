# Parallel prep: research.no1kmedi.com + clinic/no1kmedi portal + mkmlab retire checklist.
# Local: CF DNS ensure + mkmlab probe. VPS steps printed for SSH.
param(
    [switch]$ApplyCloudflareDns,
    [switch]$SkipMkmlabProbe,
    [switch]$SyncMkmlabToVps
)

$ErrorActionPreference = "Stop"
$root = if ($PSScriptRoot) { Split-Path $PSScriptRoot -Parent } else { (Get-Location).Path }
Set-Location $root

$steps = [System.Collections.Generic.List[object]]::new()

function Add-Step($name, $exit, $note) {
    $steps.Add([ordered]@{ step = $name; exit_code = $exit; note = $note }) | Out-Null
}

& py (Join-Path $root "scripts\ensure_no1kmedi_research_clinic_cloudflare_dns_v1.py") @(
    if (-not $ApplyCloudflareDns) { "--dry-run" }
)
Add-Step "ensure_no1kmedi_research_clinic_cloudflare_dns_v1" $LASTEXITCODE $(if ($ApplyCloudflareDns) { "applied" } else { "dry-run" })

if (-not $SkipMkmlabProbe) {
    & py (Join-Path $root "scripts\probe_mkmlab_space_readiness_v1.py")
    Add-Step "probe_mkmlab_space_readiness_v1" $LASTEXITCODE "legacy mkmlab.space"
}

if ($SyncMkmlabToVps) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1")
    Add-Step "Sync-MkmlabRedesignToVps_v1" $LASTEXITCODE "static to /var/www/mkmlab"
}

Push-Location (Join-Path $root "projects\no1kmedi")
& npm run sync:marketing-copy 2>$null
if ($LASTEXITCODE -ne 0) {
    node scripts/sync-marketing-site-copy.mjs
}
Add-Step "sync_marketing_copy" $LASTEXITCODE "public-copy.bundle.js"
Pop-Location

$vps = @(
    "sudo bash scripts/deploy/linux/apply_research_no1kmedi_nginx_v1.sh -y",
    "sudo certbot certonly --nginx -d research.no1kmedi.com  # if missing",
    "sudo bash scripts/deploy/linux/apply_clinic_no1kmedi_nginx_v1.sh -y",
    "sudo certbot certonly --nginx -d clinic.no1kmedi.com -d www.clinic.no1kmedi.com",
    "sudo bash scripts/deploy/linux/apply_no1kmedi_com_portal_nginx_v1.sh -y  # resolve apex vhost conflict first",
    "sudo bash scripts/deploy/linux/apply_mkmlab_space_retire_301_v1.sh -y  # after research probe OK",
    "pm2 restart no1kmedi-com  # middleware clinic hosts"
)

$out = @{
    schema     = "no1kmedi_domain_parallel_migrate_v1"
    at_utc     = (Get-Date).ToUniversalTime().ToString("o")
    steps      = $steps
    vps_manual = $vps
    ssot       = @(
        "docs/final/MKM_DOMAIN_CLINICAL_LANE_V1.md",
        "docs/final/MKM_DOMAIN_PORTFOLIO_POINTER_V1.md"
    )
}
$outPath = Join-Path $root "reports\no1kmedi_domain_parallel_migrate_latest.json"
$out | ConvertTo-Json -Depth 6 | Set-Content -Path $outPath -Encoding utf8

Write-Host "Wrote $outPath"
$failed = @($steps | Where-Object { $_.exit_code -ne 0 })
if ($failed.Count -gt 0) {
    Write-Host "Local steps with non-zero exit:" -ForegroundColor Yellow
    $failed | ForEach-Object { Write-Host "  $($_.step) exit=$($_.exit_code)" }
}
Write-Host "`nVPS (SSH) recommended order:" -ForegroundColor Cyan
$vps | ForEach-Object { Write-Host "  $_" }
exit $(if ($failed.Count -gt 0) { 1 } else { 0 })
