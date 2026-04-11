<#
.SYNOPSIS
  Adds -WindowStyle Hidden to workspace C:\workspace scheduled tasks (PowerShell hosts)
  and wraps direct Python/py/cmd launches to reduce console flash.

.PARAMETER DryRun
  Print planned changes only; do not modify tasks.

.PARAMETER WorkspaceRoot
  Only tasks whose action references this path are considered (default: C:\workspace).
#>
[CmdletBinding()]
param(
    [string]$WorkspaceRoot = "C:\workspace",
    [switch]$DryRun
)

Set-StrictMode -Version 3.0
$ErrorActionPreference = "Stop"

$script:scriptIsAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)
if (-not $script:scriptIsAdmin) {
    Write-Warning "Not running elevated: tasks that require Administrator (or run-as SYSTEM) may fail with Access Denied. Use scripts/Run-OptimizeWorkspaceScheduledTasksElevated.ps1 to finish."
}

function Test-HasWindowStyleHidden([string]$Arguments) {
    return [bool]($Arguments -match '(?i)-WindowStyle\s+Hidden')
}

function Add-HiddenToPowerShellArguments([string]$Arguments) {
    if (Test-HasWindowStyleHidden $Arguments) { return $Arguments }
    if ($Arguments -match '(?i)^(\s*-NoProfile\s+)') {
        return $Arguments -replace '(?i)^(\s*-NoProfile\s+)', '$1-WindowStyle Hidden '
    }
    return "-WindowStyle Hidden $Arguments"
}

function Get-ExecuteBaseName([string]$Execute) {
    if ([string]::IsNullOrWhiteSpace($Execute)) { return "" }
    try {
        return [System.IO.Path]::GetFileName($Execute.Trim()).ToLowerInvariant()
    }
    catch {
        return $Execute.Trim().ToLowerInvariant()
    }
}

function Test-IsPowerShellHost([string]$Execute) {
    $b = Get-ExecuteBaseName $Execute
    return ($b -eq "powershell.exe" -or $b -eq "powershell" -or $b -eq "pwsh.exe" -or $b -eq "pwsh")
}

function Test-IsPythonHost([string]$Execute) {
    $b = Get-ExecuteBaseName $Execute
    return ($b -eq "python.exe" -or $b -eq "python" -or $b -eq "pythonw.exe" -or $b -eq "py.exe" -or $b -eq "py")
}

function Wrap-PythonLikeCommand([string]$PythonExe, [string]$Arguments, [string]$WorkingDirectory) {
    $py = $PythonExe.Trim()
    $argsPart = if ($Arguments) { $Arguments.Trim() } else { "" }
    $inner = "& '$($py.Replace("'", "''"))' $argsPart"
    if ($WorkingDirectory -and $WorkingDirectory.Trim()) {
        $wd = $WorkingDirectory.Trim()
        $inner = "Set-Location -LiteralPath '$($wd.Replace("'", "''"))'; $inner"
    }
    return "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command `"$inner`""
}

function Wrap-CmdCommand([string]$CmdExe, [string]$Arguments, [string]$WorkingDirectory) {
    $c = $CmdExe.Trim()
    $a = if ($Arguments) { $Arguments.Trim() } else { "" }
    $inner = "& '$($c.Replace("'", "''"))' $(if ($a) { $a } else { '' })"
    if ($WorkingDirectory -and $WorkingDirectory.Trim()) {
        $wd = $WorkingDirectory.Trim()
        $inner = "Set-Location -LiteralPath '$($wd.Replace("'", "''"))'; $inner"
    }
    return "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -Command `"$inner`""
}

$plan = New-Object System.Collections.Generic.List[object]
$all = Get-ScheduledTask
foreach ($t in $all) {
    try {
        [xml]$xml = Export-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath -ErrorAction Stop
        $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
        $ns.AddNamespace("t", "http://schemas.microsoft.com/windows/2004/02/mit/task")
        $execNodes = $xml.SelectNodes("//t:Exec", $ns)
        if ($execNodes.Count -eq 0) { continue }
        $exec = $execNodes[0]
        $cmdNode = $exec.SelectSingleNode("t:Command", $ns)
        $argNode = $exec.SelectSingleNode("t:Arguments", $ns)
        $origCmd = if ($cmdNode) { [string]$cmdNode.InnerText } else { "" }
        $origArgs = if ($argNode) { [string]$argNode.InnerText } else { "" }
        $cmd = ($origCmd + " " + $origArgs)
        if ($cmd -notmatch [regex]::Escape($WorkspaceRoot)) { continue }

        $origWd = $null
        $wdNode = $exec.SelectSingleNode("t:WorkingDirectory", $ns)
        if ($wdNode) { $origWd = [string]$wdNode.InnerText }

        $newCmd = $origCmd
        $newArgs = $origArgs
        $change = "none"

        if (Test-IsPowerShellHost $origCmd) {
            if (-not (Test-HasWindowStyleHidden $origArgs)) {
                $newArgs = Add-HiddenToPowerShellArguments $origArgs
                $change = "ps_hidden"
            }
        }
        elseif (Test-IsPythonHost $origCmd) {
            $newCmd = "powershell.exe"
            $newArgs = Wrap-PythonLikeCommand -PythonExe $origCmd -Arguments $origArgs -WorkingDirectory $origWd
            $change = "wrap_python"
        }
        elseif ((Get-ExecuteBaseName $origCmd) -eq "cmd.exe") {
            $newCmd = "powershell.exe"
            $newArgs = Wrap-CmdCommand -CmdExe $origCmd -Arguments $origArgs -WorkingDirectory $origWd
            $change = "wrap_cmd"
        }

        if ($change -eq "none") { continue }

        $plan.Add([pscustomobject]@{
            TaskPath   = $t.TaskPath
            TaskName   = $t.TaskName
            State      = $t.State
            Change     = $change
            OldCommand = $origCmd
            NewCommand = $newCmd
            OldArgs    = $origArgs
            NewArgs    = $newArgs
            Xml        = $xml
        })
    }
    catch {
        Write-Warning "Skip $($t.TaskPath)$($t.TaskName): $($_.Exception.Message)"
    }
}

$reportDir = Join-Path $WorkspaceRoot "reports"
if (-not (Test-Path $reportDir)) { New-Item -ItemType Directory -Path $reportDir -Force | Out-Null }
$planPath = Join-Path $reportDir "workspace_scheduled_tasks_optimize_plan_latest.json"
$plan | Select-Object TaskPath, TaskName, State, Change, OldCommand, NewCommand, OldArgs, NewArgs | ConvertTo-Json -Depth 6 | Set-Content -Encoding UTF8 $planPath
Write-Host "Planned updates:" $plan.Count "Report:" $planPath

if ($DryRun) {
    exit 0
}

$ok = 0
$fail = 0
$failedNames = New-Object System.Collections.Generic.List[string]
foreach ($p in $plan) {
    try {
        [xml]$x = $p.Xml.OuterXml
        $ns = New-Object System.Xml.XmlNamespaceManager($x.NameTable)
        $ns.AddNamespace("t", "http://schemas.microsoft.com/windows/2004/02/mit/task")
        $execNodes = $x.SelectNodes("//t:Exec", $ns)
        $exec = $execNodes[0]
        $cmdNode = $exec.SelectSingleNode("t:Command", $ns)
        $argNode = $exec.SelectSingleNode("t:Arguments", $ns)
        if ($cmdNode) {
            $cmdNode.InnerText = $p.NewCommand
        }
        else {
            $newCmdEl = $x.CreateElement("Command", "http://schemas.microsoft.com/windows/2004/02/mit/task")
            $newCmdEl.InnerText = $p.NewCommand
            [void]$exec.AppendChild($newCmdEl)
        }
        if ($argNode) {
            $argNode.InnerText = $p.NewArgs
        }
        else {
            $newArgEl = $x.CreateElement("Arguments", "http://schemas.microsoft.com/windows/2004/02/mit/task")
            $newArgEl.InnerText = $p.NewArgs
            [void]$exec.AppendChild($newArgEl)
        }
        if ($p.Change -eq "wrap_python" -or $p.Change -eq "wrap_cmd") {
            $wdNode = $exec.SelectSingleNode("t:WorkingDirectory", $ns)
            if ($wdNode) { [void]$exec.RemoveChild($wdNode) }
        }
        Register-ScheduledTask -Xml $x.OuterXml -TaskName $p.TaskName -TaskPath $p.TaskPath -Force | Out-Null
        $ok++
    }
    catch {
        Write-Warning "Failed $($p.TaskPath)$($p.TaskName): $($_.Exception.Message)"
        [void]$failedNames.Add(($p.TaskPath + $p.TaskName))
        $fail++
    }
}

$failLog = Join-Path $reportDir "workspace_scheduled_tasks_optimize_failed_latest.txt"
$failedNames | Set-Content -Encoding UTF8 $failLog
Write-Host "Applied OK:" $ok "Failed:" $fail
if ($fail -gt 0) {
    Write-Host "Failed task list:" $failLog
    exit 1
}
