#Requires -Version 5.1
<#
.SYNOPSIS
  Fuse LOCAL_VS_VPS two axes: code sync vs PM2 restart vs git pull semantics.

.DESCRIPTION
  Read-only by default. Produces docs/final/artifacts/vps_destiny_fused_sync_gate_v1_latest.json

  SSOT: docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md
  VPS path: /opt/mkm-destiny-ai-41e38ec6 (vps-mkmlife)

.PARAMETER BackupPath
  Optional path to completed backup dir on VPS (informational only).

.PARAMETER SkipSsh
  Local-only git snapshot; skip VPS probe.

.PARAMETER IncludeBundleDryRun
  Run Invoke-VpsDestinyBundleSync.ps1 -DryRun when code sync may be needed.

.PARAMETER SshKeyPath
  Optional SSH key (default: use ssh config for VpsHost).
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$VpsHost = "vps-mkmlife",
    [string]$DestinyRoot = "/opt/mkm-destiny-ai-41e38ec6",
    [string]$Pm2App = "bitcoin-live-small-24h",
    [string]$GitRemote = "origin",
    [string]$GitBranch = "main",
    [string]$BackupPath = "",
    [string]$SshKeyPath = "",
    [switch]$SkipSsh,
    [switch]$IncludeBundleDryRun
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot

$outPath = Join-Path $WorkspaceRoot "docs/final/artifacts/vps_destiny_fused_sync_gate_v1_latest.json"
$utc = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")

function Get-LocalGitSnapshot {
    $branch = (git rev-parse --abbrev-ref HEAD).Trim()
    $head = (git rev-parse HEAD).Trim()
    $dirty = @(git status --porcelain).Count
    $behind = $null
    $ahead = $null
    $remoteHead = $null
    $null = git rev-parse --verify "${GitRemote}/${GitBranch}" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $remoteHead = (git rev-parse "${GitRemote}/${GitBranch}").Trim()
        $behind = [int]((git rev-list --count "HEAD..${GitRemote}/${GitBranch}").Trim())
        $ahead = [int]((git rev-list --count "${GitRemote}/${GitBranch}..HEAD").Trim())
    }
    return @{
        branch       = $branch
        head         = $head
        remote       = "${GitRemote}/${GitBranch}"
        remote_head  = $remoteHead
        behind       = $behind
        ahead        = $ahead
        porcelain_lines = $dirty
    }
}

function Invoke-SshJson {
    param([string]$RemoteScript)
    $sshArgs = @("-o", "BatchMode=yes", "-o", "ConnectTimeout=20")
    if ($SshKeyPath -and (Test-Path -LiteralPath $SshKeyPath)) {
        $sshArgs = @("-i", $SshKeyPath) + $sshArgs
    }
    $normalized = ($RemoteScript -replace "`r`n", "`n").TrimEnd() + "`n"
    $encoded = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($normalized))
    $cmd = "echo $encoded | base64 -d | bash"
    $prevEap = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $raw = & ssh @sshArgs $VpsHost $cmd 2>&1
    $sshExit = $LASTEXITCODE
    $ErrorActionPreference = $prevEap
    if ($sshExit -ne 0) {
        return @{ ok = $false; error = ($raw | Out-String).Trim(); ssh_exit = $sshExit }
    }
    $text = ($raw | Out-String).Trim()
    try {
        return ($text | ConvertFrom-Json)
    } catch {
        if ($text -match '\{[\s\S]*\}') {
            try {
                return ($Matches[0] | ConvertFrom-Json)
            } catch {
                return @{ ok = $false; error = "json_parse_failed"; raw = $text }
            }
        }
        return @{ ok = $false; error = "json_parse_failed"; raw = $text }
    }
}

$localGit = Get-LocalGitSnapshot
$vpsGit = $null
$pm2Health = $null

if (-not $SkipSsh) {
    $vpsProbe = @"
set -euo pipefail
cd '$DestinyRoot'
git fetch $GitRemote 2>/dev/null || true
H=`$(git rev-parse HEAD)
RH=`$(git rev-parse $GitRemote/$GitBranch 2>/dev/null || echo '')
BEHIND=0
AHEAD=0
if [ -n "`$RH" ]; then
  BEHIND=`$(git rev-list --count HEAD..$GitRemote/$GitBranch 2>/dev/null || echo 0)
  AHEAD=`$(git rev-list --count $GitRemote/$GitBranch..HEAD 2>/dev/null || echo 0)
fi
python3 - <<'PY'
import json, subprocess, os
root = "$DestinyRoot"
def sh(cmd):
    return subprocess.check_output(cmd, shell=True, text=True).strip()
data = {
  "ok": True,
  "destiny_root": root,
  "head": sh("git rev-parse HEAD"),
  "head_short": sh("git rev-parse --short HEAD"),
  "branch": sh("git rev-parse --abbrev-ref HEAD"),
  "remote": "$GitRemote/$GitBranch",
  "remote_head": sh("git rev-parse $GitRemote/$GitBranch 2>/dev/null || true") or None,
  "behind": int(sh("git rev-list --count HEAD..$GitRemote/$GitBranch 2>/dev/null || echo 0")),
  "ahead": int(sh("git rev-list --count $GitRemote/$GitBranch..HEAD 2>/dev/null || echo 0")),
  "binance_client_has_4067": False,
}
p = os.path.join(root, "projects/bitcoin-trading/src/api/binance_client.py")
if os.path.isfile(p):
    txt = open(p, encoding="utf-8", errors="replace").read()
    data["binance_client_has_4067"] = "-4067" in txt or "4067" in txt
print(json.dumps(data))
PY
"@
    $vpsGit = Invoke-SshJson -RemoteScript $vpsProbe

    $healthScript = Join-Path $WorkspaceRoot "projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_health_snapshot.sh"
    if (Test-Path -LiteralPath $healthScript) {
        $sshArgs = @("-o", "BatchMode=yes", "-o", "ConnectTimeout=20")
        if ($SshKeyPath -and (Test-Path -LiteralPath $SshKeyPath)) {
            $sshArgs = @("-i", $SshKeyPath) + $sshArgs
        }
        $remoteSh = "$DestinyRoot/projects/bitcoin-trading/ops/v2/ssh/vps_pm2_bitcoin_live_health_snapshot.sh"
        $prevEap2 = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        $hout = & ssh @sshArgs $VpsHost "PM2_APP_NAME=$Pm2App EXPECT_CWD_PREFIX=$DestinyRoot bash $remoteSh" 2>&1
        $hExit = $LASTEXITCODE
        $ErrorActionPreference = $prevEap2
        $htail = ($hout | Out-String).Trim()
        if ($htail.Length -gt 1200) { $htail = $htail.Substring($htail.Length - 1200) }
        $pm2Health = @{
            exit_code = $hExit
            tail      = $htail
            verdict   = if (($hout | Out-String) -match 'verdict:\s*(\S+)') { $Matches[1] } else { $null }
        }
    }
}

# --- Fused decisions (two axes) ---
$codeSync = "HOLD_NO_VPS_PULL"
$codeRationale = @(
    "VPS git pull only applies when behind remote; does not ship local PC commits."
)
$pm2Restart = "HOLD"
$pm2Rationale = @("PM2 healthy and no code change applied this session.")

if ($vpsGit -and $vpsGit.ok -eq $true) {
    if ([int]$vpsGit.behind -eq 0) {
        $codeRationale += "VPS behind_${GitRemote}_${GitBranch}=$($vpsGit.behind) — pull would fetch nothing new."
    } else {
        $codeSync = "VPS_PULL_ONLY_IF_APPROVED"
        $codeRationale += "VPS behind=$($vpsGit.behind) — still not local→VPS; only updates VPS from remote."
    }
    if ([int]$vpsGit.ahead -gt 0) {
        $codeRationale += "VPS ahead=$($vpsGit.ahead) — VPS-only commits on remote; avoid reset/hard pull without policy."
    }
}

if ($vpsGit -and $vpsGit.ok -eq $true -and $vpsGit.binance_client_has_4067 -eq $true) {
    $codeRationale += "VPS binance_client (-4067 handling) present at src/api/binance_client.py after recent hotfix."
}
if ($localGit.ahead -gt 0 -or $localGit.porcelain_lines -gt 0) {
    if ($vpsGit -and $vpsGit.binance_client_has_4067) {
        $codeSync = "HOLD_HOTFIX_APPLIED_BUNDLE_DEFERRED"
        $codeRationale += "Hotfix path applied; full bundle deferred while local tree dirty/unpushed."
    } else {
        $codeSync = "SHIP_LOCAL_TO_VPS_BUNDLE_OR_HOTFIX"
        $codeRationale += "Local has unpushed or uncommitted work — use bundle sync or bitcoin-trading hotfix scp, not VPS pull."
    }
}
if ($pm2Health -and $pm2Health.verdict -eq "GO" -and $codeSync -eq "HOLD_HOTFIX_APPLIED_BUNDLE_DEFERRED") {
    $pm2Restart = "HOLD"
    $pm2Rationale = @("Hotfix already applied; PM2 GO — no further restart this cycle.")
}

if ($pm2Health -and $pm2Health.verdict -and $pm2Health.verdict -ne "GO") {
    $pm2Restart = "INVESTIGATE_BEFORE_RESTART"
    $pm2Rationale = @("PM2 snapshot verdict=$($pm2Health.verdict).")
} elseif ($codeSync -eq "SHIP_LOCAL_TO_VPS_BUNDLE_OR_HOTFIX") {
    $pm2Restart = "RESTART_APP_ONLY_AFTER_CODE_APPLIED"
    $pm2Rationale = @(
        "After hotfix/bundle merge, restart single app: pm2 restart $Pm2App (never restart all)."
    )
}

$bundleDryRun = $null
if ($IncludeBundleDryRun -and $codeSync -eq "SHIP_LOCAL_TO_VPS_BUNDLE_OR_HOTFIX") {
    $bundleScript = Join-Path $WorkspaceRoot "scripts/Invoke-VpsDestinyBundleSync.ps1"
    if (Test-Path -LiteralPath $bundleScript) {
        $bundleDryRun = & powershell -NoProfile -ExecutionPolicy Bypass -File $bundleScript -DryRun 2>&1 | Out-String
    }
}

$doc = [ordered]@{
    schema              = "vps_destiny_fused_sync_gate_v1"
    generated_at_utc    = $utc
  classification        = "INTERNAL_ONLY"
    ssh_host            = $VpsHost
    destiny_root        = $DestinyRoot
    pm2_app             = $Pm2App
    backup_path_on_vps  = $(if ($BackupPath) { $BackupPath } else { $null })
    two_axis_ssot       = "docs/final/LOCAL_VS_VPS_ONE_RULE_WORKFLOW.md"
    axis_code_sync      = @{
        recommendation = $codeSync
        rationale      = $codeRationale
        vps_git_pull_now = $false
        bundle_sync_path = "scripts/Invoke-VpsDestinyBundleSync.ps1"
        hotfix_path      = "scripts/Sync-VpsBitcoinTradingHotfix_v1.ps1 -WhatIfOnly"
    }
    axis_pm2_restart    = @{
        recommendation = $pm2Restart
        rationale      = $pm2Rationale
        restart_now    = $false
        restart_cmd    = "ssh $VpsHost `"cd $DestinyRoot && pm2 restart $Pm2App`""
    }
    local_git           = $localGit
    vps_git             = $vpsGit
    pm2_health          = $pm2Health
    bundle_sync_dry_run = $bundleDryRun
    boundary_ack        = @(
        "B-track prophecy READY ≠ live trading GO."
        "Code sync success ≠ ENABLE_TRADING ON."
        "Do not reset --hard VPS without explicit approval when ahead>0."
    )
}

New-Item -ItemType Directory -Force -Path (Split-Path -Parent $outPath) | Out-Null
($doc | ConvertTo-Json -Depth 8) + "`n" | Set-Content -LiteralPath $outPath -Encoding utf8
Write-Host "WROTE $outPath" -ForegroundColor Green
Write-Host "code_sync=$codeSync pm2=$pm2Restart" -ForegroundColor Cyan
if ($pm2Health.verdict) { Write-Host "pm2_verdict=$($pm2Health.verdict)" -ForegroundColor Cyan }
