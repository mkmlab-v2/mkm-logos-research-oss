# Upload + start productive burn on Cloud Shell via gcloud ssh/scp (no browser paste).
param(
    [string]$Project = "gen-lang-client-0846393371",
    [string]$RequiredAccount = "jema12@mkmlife.com",
    [switch]$SkipAccountCheck,
    [switch]$PostIamWave,
    [string]$HostKey = "ecdsa-sha2-nistp256 256 SHA256:5/CRJcYwiwMfrafnBjNHe6RWC7qrWlUAKmrtab0v2wQ"
)
# PuTTY host-key prompt: always pass -batch -hostkey (see Invoke-GcpCloudShellSshNoPrompt_v1.ps1).
# Plain `gcloud cloud-shell ssh` hangs on "Store key in cache?" — agent terminals cannot answer.

$ErrorActionPreference = "Stop"
$active = (gcloud auth list --filter=status:ACTIVE --format="value(account)" 2>$null | Select-Object -First 1)
if (-not $SkipAccountCheck -and $RequiredAccount -and $active -ne $RequiredAccount) {
    Write-Error "Active gcloud account is '$active' — need '$RequiredAccount'. Run: gcloud auth login $RequiredAccount && gcloud config set account $RequiredAccount"
}
$Root = Split-Path -Parent $PSScriptRoot
$Tar = Join-Path $Root "reports/gcp_productive_burn_shell_pkg_v1.tar.gz"
if (-not (Test-Path -LiteralPath $Tar)) {
    py (Join-Path $Root "scripts/pack_gcp_productive_burn_for_gcs_v1.py") | Out-Host
    if ($LASTEXITCODE -ne 0) { throw "pack_gcp_productive_burn_for_gcs_v1 failed" }
}
$LogPullDir = Join-Path $Root "reports/sandbox/gcp_productive_burn_logs"

$scpFlags = @(
    "--project", $Project,
    "--scp-flag=-batch",
    "--scp-flag=-hostkey",
    "--scp-flag=$HostKey"
)
$sshFlags = @(
    "--project", $Project,
    "--authorize-session",
    "--ssh-flag=-batch",
    "--ssh-flag=-hostkey",
    "--ssh-flag=$HostKey"
)

Write-Host "=== SCP shell pkg tar (account: $active) ==="
& gcloud cloud-shell scp @scpFlags "localhost:$Tar" "cloudshell:pb_pkg.tar.gz"

$resumeScript = if ($PostIamWave) { "gcp_productive_burn_resume_post_iam_v1.sh" } else { "gcp_productive_burn_resume_genlang.sh" }
$remote = @(
    "tar xzf ~/pb_pkg.tar.gz -C ~",
    "sed -i 's/\r$//' ~/gcp_productive_burn_*.sh ~/gcp_productive_burn_lane_runner_v1.py",
    "test -f ~/gcp_productive_burn_lane_runner_v1.py || { echo INSTALL_FAIL; exit 1; }",
    "chmod +x ~/$resumeScript",
    "bash ~/$resumeScript",
    "sleep 5",
    "pgrep -af gcp_productive_burn_lane_runner || echo NO_PROC",
    "wc -l ~/productive_burn_logs/*.jsonl 2>/dev/null || echo NO_JSONL"
) -join "; "

Write-Host "=== SSH resume ==="
& gcloud cloud-shell ssh @sshFlags --command=$remote

if ($LASTEXITCODE -eq 0) {
    New-Item -ItemType Directory -Force -Path $LogPullDir | Out-Null
    Write-Host "=== SCP logs to $LogPullDir ==="
    if ($PostIamWave) {
        & gcloud cloud-shell scp @scpFlags "cloudshell:/home/giryun288/productive_burn_logs/asset_rag_P4a_genlang.jsonl" "localhost:$LogPullDir/asset_rag_P4a_genlang.jsonl"
        & gcloud cloud-shell scp @scpFlags "cloudshell:/home/giryun288/productive_burn_logs/btrack_fills_daily_P4b_fills.jsonl" "localhost:$LogPullDir/btrack_fills_daily_P4b_fills.jsonl"
    }
    else {
        & gcloud cloud-shell scp @scpFlags "cloudshell:/home/giryun288/productive_burn_logs/asset_rag_P3a_genlang.jsonl" "localhost:$LogPullDir/asset_rag_P3a_genlang.jsonl"
        & gcloud cloud-shell scp @scpFlags "cloudshell:/home/giryun288/productive_burn_logs/btrack_fills_daily_P3b_fills.jsonl" "localhost:$LogPullDir/btrack_fills_daily_P3b_fills.jsonl"
    }
    & gcloud cloud-shell scp @scpFlags "cloudshell:/home/giryun288/productive_burn_logs/*_summary.json" "localhost:$LogPullDir/"
}
