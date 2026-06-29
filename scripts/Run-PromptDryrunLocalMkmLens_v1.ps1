#Requires -Version 5.1
<#
.SYNOPSIS
  PROMPT_DRYRUN_LOCAL — Ollama 8B + birth_anchor MKM lens few-shot [HYPO].
.EXAMPLE
  pwsh -File scripts/Run-PromptDryrunLocalMkmLens_v1.ps1
  pwsh -File scripts/Run-PromptDryrunLocalMkmLens_v1.ps1 -Strict
#>
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [string]$Model = "",
    [switch]$Sweep,
    [switch]$Strict,
    [switch]$SkipPromptCard
)

$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $WorkspaceRoot
$py = if (Get-Command py -ErrorAction SilentlyContinue) { "py" } else { "python" }
$argsList = @("scripts/run_prompt_dryrun_local_mkm_lens_v1.py")
if ($Model) { $argsList += @("--model", $Model) }
if ($Sweep) { $argsList += "--sweep-defaults" }
if ($Strict) { $argsList += "--strict" }
& $py @argsList
$code = $LASTEXITCODE
if ($code -ne 0) { exit $code }

if ($Sweep -and -not $SkipPromptCard) {
    & $py scripts/build_nemotron_lora_mkm_lens_prompt_card_v1.py
    exit $LASTEXITCODE
}

exit 0
