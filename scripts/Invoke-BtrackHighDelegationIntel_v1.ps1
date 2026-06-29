<#
.SYNOPSIS
  B-track high-delegation intel — preflight then multi-source intel JSON.

.EXAMPLE
  powershell -File scripts\Invoke-BtrackHighDelegationIntel_v1.ps1 -Lane oracle
  powershell -File scripts\Invoke-BtrackHighDelegationIntel_v1.ps1 -Lane oracle -GithubOwner squeezebits -GithubRepo blog
#>
param(
    [ValidateSet("M", "L")]
    [string]$Scale = "M",
    [ValidateSet("", "oracle", "prophecy", "ops", "infra", "design", "web_ops", "ms")]
    [string]$Lane = "oracle",
    [string]$ApprovalMap = "",
    [string]$GithubOwner = "",
    [string]$GithubRepo = "",
    [switch]$LiveAtproto,
    [int]$AtprotoLimit = 50,
    [switch]$IncludeSwarmDownstream,
    [switch]$SkipPreflight
)

$ErrorActionPreference = "Stop"
$root = if ($env:MKM_WORKSPACE_ROOT) { $env:MKM_WORKSPACE_ROOT.TrimEnd('\', '/') } else { "C:\workspace" }
Set-Location -LiteralPath $root

if (-not $SkipPreflight) {
    $pfArgs = @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', (Join-Path $root 'scripts\Invoke-MkmHighDelegationPreflight_v1.ps1'), '-Scale', $Scale)
    if ($Lane) { $pfArgs += @('-Lane', $Lane) }
    if ($ApprovalMap) { $pfArgs += @('-ApprovalMap', $ApprovalMap) }
    & powershell @pfArgs
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}

$intelArgs = @('scripts/build_btrack_high_delegation_intel_v1.py')
if ($GithubOwner -and $GithubRepo) {
    $intelArgs += @('--github-owner', $GithubOwner, '--github-repo', $GithubRepo)
}
if ($LiveAtproto) {
    $intelArgs += @('--live-atproto', '--atproto-limit', [string]$AtprotoLimit)
}
if ($IncludeSwarmDownstream) {
    $intelArgs += '--include-swarm-downstream'
}
& py @intelArgs
exit $LASTEXITCODE
