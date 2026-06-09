# Install optional post-commit hook for coding intent link PoC (research_only).
param(
    [switch]$Remove,
    [switch]$WhatIfOnly
)

$ErrorActionPreference = "Stop"
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$sample = Join-Path $PSScriptRoot "githooks\post-commit-coding-intent-link_v1.sample"
$gitDir = Join-Path $root ".git"
$hookPath = Join-Path $gitDir "hooks\post-commit"

if (-not (Test-Path -LiteralPath $gitDir)) {
    throw "Not a git repository: $root"
}
if (-not (Test-Path -LiteralPath $sample)) {
    throw "Sample hook missing: $sample"
}

if ($Remove) {
    if (Test-Path -LiteralPath $hookPath) {
        $head = Get-Content -LiteralPath $hookPath -TotalCount 3 -ErrorAction SilentlyContinue
        if ($head -match "post-commit-coding-intent-link_v1") {
            if ($WhatIfOnly) {
                Write-Host "WhatIf: would remove $hookPath"
            } else {
                Remove-Item -LiteralPath $hookPath -Force
                Write-Host "Removed MKM coding-intent post-commit hook."
            }
        } else {
            Write-Warning "post-commit exists but is not MKM-managed; skipped."
        }
    } else {
        Write-Host "No post-commit hook to remove."
    }
    exit 0
}

$content = Get-Content -LiteralPath $sample -Raw
if ($WhatIfOnly) {
    Write-Host "WhatIf: would write $hookPath"
    exit 0
}

$hooksDir = Split-Path -Parent $hookPath
if (-not (Test-Path -LiteralPath $hooksDir)) {
    New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
}
# PS 5.1 lacks utf8NoBOM; write UTF-8 without BOM via .NET.
$utf8NoBom = New-Object System.Text.UTF8Encoding $false
[System.IO.File]::WriteAllText($hookPath, $content, $utf8NoBom)
Write-Host "Installed: $hookPath"
Write-Host "Runs: py scripts/record_coding_intent_link_v1.py record --include-diff --gate-exit-code 0 --allow-partial"
Write-Host "Remove: powershell -File scripts/Install-CodingIntentLinkGitHook_v1.ps1 -Remove"
