# Full deploy: CF DNS + mkmlab sync + no1kmedi tarball + VPS nginx/certs/pm2.
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun,
    [switch]$SkipCloudflare,
    [switch]$SkipMkmlabSync,
    [switch]$SkipNo1kmediTarball,
    [switch]$SkipVpsNginx
)

$ErrorActionPreference = "Stop"
$root = $WorkspaceRoot
Set-Location $root

function Get-EnvAny([string]$name) {
    $v = [Environment]::GetEnvironmentVariable($name, "Process")
    if ($v) { return $v.Trim() }
    $v = [Environment]::GetEnvironmentVariable($name, "User")
    if ($v) { return $v.Trim() }
    return ""
}

$hostName = Get-EnvAny "MKM_VPS_HOST"
if (-not $hostName) { $hostName = "vps-mkmlife" }
$user = Get-EnvAny "MKM_VPS_USER"
if (-not $user) { $user = "root" }
$remote = "${user}@${hostName}"

$sshArgs = @()
$extra = Get-EnvAny "MKM_VPS_SCP_EXTRA_ARGS"
if ($extra) { $sshArgs = $extra -split "\s+" | Where-Object { $_ } }

$steps = [System.Collections.Generic.List[object]]::new()
function Add-Step($n, $ec, $note) { $steps.Add([ordered]@{ step = $n; exit_code = $ec; note = $note }) | Out-Null }

if (-not $SkipCloudflare) {
    $cfArgs = @()
    if ($DryRun) { $cfArgs += "--dry-run" }
    & py (Join-Path $root "scripts\ensure_no1kmedi_research_clinic_cloudflare_dns_v1.py") @cfArgs
    Add-Step "cloudflare_dns" $LASTEXITCODE $(if ($DryRun) { "dry-run" } else { "applied" })
    if (-not $DryRun) { Start-Sleep -Seconds 8 }
}

if (-not $SkipMkmlabSync) {
    if ($DryRun) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1") -DryRun
    } else {
        & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Sync-MkmlabRedesignToVps_v1.ps1")
    }
    Add-Step "mkmlab_scp" $LASTEXITCODE "/var/www/mkmlab"
}

if (-not $SkipNo1kmediTarball) {
    $tbArgs = @("-WorkspaceRoot", $root)
    if ($DryRun) { $tbArgs += "-DryRun" }
    & powershell -NoProfile -ExecutionPolicy Bypass -File (Join-Path $root "scripts\Deploy-No1kmediDestinyTarball_v1.ps1") @tbArgs
    Add-Step "no1kmedi_tarball" $LASTEXITCODE "middleware+app"
}

if (-not $SkipVpsNginx) {
    $vpsRepo = "/opt/mkm-destiny-ai-41e38ec6"
    $remoteScript = "$vpsRepo/scripts/deploy/linux/run_no1kmedi_domain_vps_deploy_v1.sh"
    $linuxLocal = Join-Path $root "scripts\deploy\linux"
    $deployFiles = @(
        "run_no1kmedi_domain_vps_deploy_v1.sh",
        "apply_research_no1kmedi_nginx_v1.sh",
        "apply_clinic_no1kmedi_nginx_v1.sh",
        "apply_no1kmedi_com_portal_nginx_v1.sh",
        "apply_no1kmedi_com_portal_http_only_v1.sh",
        "apply_mkmlab_space_retire_301_v1.sh",
        "nginx-research-no1kmedi-com.conf.example",
        "nginx-clinic-no1kmedi-com.conf.example",
        "nginx-no1kmedi-com-portal.conf.example"
    )
    if ($DryRun) {
        Write-Host "[dry-run] scp deploy linux bundle + ssh bash $remoteScript -y"
        Add-Step "vps_nginx_pm2" 0 "dry-run"
    } else {
        & ssh @($sshArgs + @($remote, "mkdir -p $vpsRepo/scripts/deploy/linux"))
        foreach ($f in $deployFiles) {
            $local = Join-Path $linuxLocal $f
            if (-not (Test-Path $local)) { throw "missing $local" }
            & scp @($sshArgs + @($local, "${remote}:${vpsRepo}/scripts/deploy/linux/"))
            if ($LASTEXITCODE -ne 0) { throw "scp $f failed" }
        }
        Add-Step "vps_scp_deploy_scripts" 0 "linux bundle"

        $pull = "cd $vpsRepo && git fetch gitea main 2>/dev/null; git pull --ff-only gitea main 2>/dev/null || true"
        & ssh @($sshArgs + @($remote, $pull))
        Add-Step "vps_git_pull" $LASTEXITCODE "best-effort"

        & ssh @($sshArgs + @($remote, "chmod +x $remoteScript $vpsRepo/scripts/deploy/linux/apply_*_no1kmedi*.sh $vpsRepo/scripts/deploy/linux/apply_mkmlab_space_retire_301_v1.sh 2>/dev/null; MKM_REPO_ROOT=$vpsRepo bash $remoteScript -y"))
        Add-Step "vps_nginx_pm2" $LASTEXITCODE "nginx+certbot+pm2"
    }
}

# Post probes
if (-not $DryRun) {
    $urls = @(
        "https://research.no1kmedi.com/",
        "https://clinic.no1kmedi.com/",
        "https://mkmlab.space/"
    )
    foreach ($u in $urls) {
        try {
            $r = Invoke-WebRequest -Uri $u -MaximumRedirection 5 -TimeoutSec 25 -UseBasicParsing
            Add-Step "probe_$u" 0 "status=$($r.StatusCode)"
        } catch {
            Add-Step "probe_$u" 1 $_.Exception.Message
        }
    }
}

$out = @{
    schema = "no1kmedi_domain_vps_deploy_v1"
    at_utc = (Get-Date).ToUniversalTime().ToString("o")
    vps    = $remote
    steps  = $steps
}
$outPath = Join-Path $root "reports\no1kmedi_domain_vps_deploy_latest.json"
$out | ConvertTo-Json -Depth 6 | Set-Content -Path $outPath -Encoding utf8
Write-Host "Wrote $outPath" -ForegroundColor Green

$bad = @($steps | Where-Object { $_.exit_code -ne 0 })
if ($bad.Count -gt 0) { exit 1 }
exit 0
