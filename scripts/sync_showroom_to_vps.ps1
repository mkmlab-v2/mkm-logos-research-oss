# Wrapper: run from repo root (PATH-independent).
# Forwards to bitcoin-trading ops script; pass-through args (e.g. -RefreshStaging -DryRun).

param(
    [string]$WorkspaceRoot = "",
    [switch]$RefreshStaging,
    [switch]$DryRun,
    [switch]$SkipDotenvUserSync,
    [switch]$AllowPasswordPrompt
)

$ErrorActionPreference = "Stop"
$root = if ([string]::IsNullOrWhiteSpace($WorkspaceRoot)) {
    (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
} else {
    $WorkspaceRoot
}

$target = Join-Path $root "projects\bitcoin-trading\ops\windows-rehearsal\sync_showroom_to_vps.ps1"
if (-not (Test-Path -LiteralPath $target)) {
    throw "Missing: $target"
}

$argList = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $target, "-WorkspaceRoot", $root)
if ($RefreshStaging) { $argList += "-RefreshStaging" }
if ($DryRun) { $argList += "-DryRun" }
if ($SkipDotenvUserSync) { $argList += "-SkipDotenvUserSync" }
if ($AllowPasswordPrompt) { $argList += "-AllowPasswordPrompt" }

if (Get-Command pwsh -ErrorAction SilentlyContinue) {
    & pwsh @argList
} else {
    & powershell.exe @argList
}
exit $LASTEXITCODE
