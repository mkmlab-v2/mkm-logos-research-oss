[CmdletBinding(SupportsShouldProcess = $true)]
param(
    [Parameter(Mandatory = $false)]
    [ValidateSet('lock', 'mkm')]
    [string]$PrimaryAlias = 'lock',

    [Parameter(Mandatory = $false)]
    [switch]$IncludeKoreanAlias,

    [Parameter(Mandatory = $false)]
    [switch]$ReloadProfile
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$MarkerBegin = '# MKM LocalLock shell alias BEGIN (Register-LocalLockShellAlias_v1.ps1)'
$MarkerEnd = '# MKM LocalLock shell alias END'
$LocalLockScript = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot 'Invoke-LocalLock_v1.ps1')).Path
# PS 5.1 may read BOM-less UTF-8 .ps1 as system ANSI — build Korean alias from code points.
$KoreanAliasName = -join ([char[]](0xBE44, 0xBC88, 0xAD00, 0xB9AC))

if (-not (Test-Path -LiteralPath $LocalLockScript)) {
    throw "LocalLock script not found: $LocalLockScript"
}

if (-not (Test-Path -LiteralPath $PROFILE)) {
    $profileDir = Split-Path -Parent $PROFILE
    if (-not (Test-Path -LiteralPath $profileDir)) {
        New-Item -ItemType Directory -Path $profileDir -Force | Out-Null
    }
    New-Item -ItemType File -Path $PROFILE -Force | Out-Null
}

$escapedScript = $LocalLockScript.Replace("'", "''")
$block = @"
$MarkerBegin
function global:$PrimaryAlias {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File '$escapedScript' @args
    if (`$null -ne `$LASTEXITCODE) { exit [int]`$LASTEXITCODE }
}
"@

if ($IncludeKoreanAlias) {
    $block += @"

function global:${KoreanAliasName} {
    & global:$PrimaryAlias menu @args
}
"@
}

$block += "`n$MarkerEnd`n"

$existing = Get-Content -LiteralPath $PROFILE -Raw -Encoding UTF8
if ([string]::IsNullOrEmpty($existing)) {
    $existing = ''
}

if ($existing -match [regex]::Escape($MarkerBegin)) {
  $pattern = [regex]::Escape($MarkerBegin) + '[\s\S]*?' + [regex]::Escape($MarkerEnd)
  $updated = [regex]::Replace($existing, $pattern, $block.TrimEnd())
}
else {
  $updated = ($existing.TrimEnd() + "`n`n" + $block).TrimEnd() + "`n"
}

if ($PSCmdlet.ShouldProcess($PROFILE, 'Install LocalLock shell alias block')) {
    $utf8Bom = New-Object System.Text.UTF8Encoding $true
    [System.IO.File]::WriteAllText($PROFILE, $updated, $utf8Bom)
    Write-Host "[LocalLock] Installed alias '$PrimaryAlias' -> $LocalLockScript" -ForegroundColor Green
    if ($IncludeKoreanAlias) {
        Write-Host "[LocalLock] Installed Korean alias '$KoreanAliasName' -> $PrimaryAlias menu" -ForegroundColor Green
    }
    Write-Host "[LocalLock] Open a new terminal or run: . `$PROFILE" -ForegroundColor Cyan
}

if ($ReloadProfile -and (Test-Path -LiteralPath $PROFILE)) {
    . $PROFILE
    Write-Host "[LocalLock] Profile reloaded in current session." -ForegroundColor Cyan
}
