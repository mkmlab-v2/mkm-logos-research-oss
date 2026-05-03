#requires -Version 5.1
<#
.SYNOPSIS
  만세력 봇 → 완전 융합 JSON → 명리 독립 렌즈 v1 (한 번에).

.EXAMPLE
  pwsh -File scripts/Run-MyeongniLensChainFromBot_v1.ps1 -DemoSmoke
  pwsh -File scripts/Run-MyeongniLensChainFromBot_v1.ps1 -ProfileJson C:\path\profile.json
#>
param(
  [string] $ProfileJson = "",
  [string] $FusionJson = "",
  [switch] $DemoSmoke,
  [string] $BotOut = "",
  [string] $FusionOut = "",
  [string] $LensOut = "",
  [switch] $Compact
)

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

$py = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { "py" }
$script = Join-Path $root "scripts\run_myeongni_lens_chain_from_bot_v1.py"
$argsList = @($script)
if ($DemoSmoke) {
  $argsList += "--demo-smoke"
} elseif ($FusionJson) {
  $argsList += "--fusion-json", $FusionJson
} elseif ($ProfileJson) {
  $argsList += "--profile-json", $ProfileJson
} else {
  Write-Error "Specify -DemoSmoke, -ProfileJson, or -FusionJson"
}
if ($BotOut) { $argsList += "--bot-out", $BotOut }
if ($FusionOut) { $argsList += "--fusion-out", $FusionOut }
if ($LensOut) { $argsList += "--lens-out", $LensOut }
if ($Compact) { $argsList += "--compact" }

& $py @argsList
exit $LASTEXITCODE
