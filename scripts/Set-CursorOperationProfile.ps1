param(
    [ValidateSet("Hard", "Soft")]
    [string]$Mode = "Hard",
    [switch]$WhatIf
)

$ErrorActionPreference = "Stop"

$workspaceRoot = "C:\workspace"
$reportsDir = Join-Path $workspaceRoot "reports"
$workspaceMcpPath = Join-Path $workspaceRoot ".cursor\mcp.json"
$workspaceMcpBackupPath = Join-Path $reportsDir "cursor_mcp_workspace_soft_backup.json"
$userSettingsPath = "C:\Users\PRO\AppData\Roaming\Cursor\User\settings.json"
$startupDir = "C:\Users\PRO\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup"
$startupItems = @("cursor_restart_health_check.vbs", "Ollama.lnk")

function Set-SettingLine {
    param(
        [string]$Path,
        [string]$Key,
        [string]$JsonValueLiteral
    )
    if (-not (Test-Path $Path)) { return }
    $raw = Get-Content -Path $Path -Raw -Encoding UTF8
    $pattern = '(?m)^\s*"' + [regex]::Escape($Key) + '"\s*:\s*.*$'
    $replacement = '  "' + $Key + '": ' + $JsonValueLiteral + ','
    if ($raw -match $pattern) {
        $raw = [regex]::Replace($raw, $pattern, $replacement)
    } else {
        $insert = "`r`n$replacement`r`n"
        $raw = $raw -replace '(?s)\}\s*$', "$insert}"
    }
    if ($WhatIf) {
        Write-Output "[WhatIf] update setting $Key=$JsonValueLiteral"
    } else {
        Set-Content -Path $Path -Value $raw -Encoding UTF8
    }
}

function Set-WorkspaceMcp {
    param([bool]$Enable)
    if (-not (Test-Path $reportsDir)) {
        if (-not $WhatIf) { New-Item -ItemType Directory -Path $reportsDir | Out-Null }
    }

    if ($Enable) {
        if (Test-Path $workspaceMcpBackupPath) {
            if ($WhatIf) {
                Write-Output "[WhatIf] restore workspace mcp.json from backup"
            } else {
                Copy-Item -Path $workspaceMcpBackupPath -Destination $workspaceMcpPath -Force
            }
        } else {
            Write-Output "WARN: no workspace MCP backup found ($workspaceMcpBackupPath)"
        }
        return
    }

    if (Test-Path $workspaceMcpPath) {
        if ($WhatIf) {
            Write-Output "[WhatIf] backup workspace mcp.json and set empty mcpServers"
        } else {
            Copy-Item -Path $workspaceMcpPath -Destination $workspaceMcpBackupPath -Force
            Set-Content -Path $workspaceMcpPath -Value "{`r`n  `"mcpServers`": {}`r`n}" -Encoding UTF8
        }
    }
}

function Set-StartupItems {
    param([bool]$Enable)
    foreach ($name in $startupItems) {
        $path = Join-Path $startupDir $name
        $disabledPath = "$path.disabled"
        if ($Enable) {
            if (Test-Path $disabledPath) {
                if ($WhatIf) {
                    Write-Output "[WhatIf] restore startup item $name"
                } else {
                    Move-Item -Path $disabledPath -Destination $path -Force
                }
            }
        } else {
            if (Test-Path $path) {
                if ($WhatIf) {
                    Write-Output "[WhatIf] disable startup item $name"
                } else {
                    Move-Item -Path $path -Destination $disabledPath -Force
                }
            }
        }
    }
}

if ($Mode -eq "Hard") {
    if ($WhatIf) {
        Write-Output "[WhatIf] run quiet scheduler profile"
    } else {
        & "C:\workspace\scripts\Set-SchedulerQuietProfile.ps1" -Mode Quiet | Out-Null
    }
    Set-SettingLine -Path $userSettingsPath -Key "mcp.enabled" -JsonValueLiteral "false"
    Set-SettingLine -Path $userSettingsPath -Key "jema12.autoStartServers" -JsonValueLiteral "false"
    Set-WorkspaceMcp -Enable:$false
    Set-StartupItems -Enable:$false
    Write-Output "mode=hard complete"
    exit 0
}

if ($WhatIf) {
    Write-Output "[WhatIf] restore scheduler profile"
} else {
    & "C:\workspace\scripts\Set-SchedulerQuietProfile.ps1" -Mode Restore | Out-Null
}
Set-SettingLine -Path $userSettingsPath -Key "mcp.enabled" -JsonValueLiteral "true"
Set-SettingLine -Path $userSettingsPath -Key "jema12.autoStartServers" -JsonValueLiteral "false"
Set-WorkspaceMcp -Enable:$true
Set-StartupItems -Enable:$true
Write-Output "mode=soft complete"
