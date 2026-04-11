# Audits Windows Scheduled Tasks whose action references C:\workspace (read-only).
# Writes CSV to reports/ if workspace root is writable.
$ErrorActionPreference = "SilentlyContinue"
$workspaceRoot = "C:\workspace"

function Get-ExeBaseName([string]$commandPath) {
    if ([string]::IsNullOrWhiteSpace($commandPath)) { return "" }
    $t = $commandPath.Trim().Trim('"')
    try {
        return [System.IO.Path]::GetFileName($t).ToLowerInvariant()
    }
    catch {
        return $t.ToLowerInvariant()
    }
}

function Get-LauncherBucket([string]$exeBase) {
    if ($exeBase -match '^(powershell|pwsh)(\.exe)?$') { return "PowerShell" }
    if ($exeBase -match '^(python|pythonw|py)(\.exe)?$') { return "PythonOrPy" }
    if ($exeBase -eq "cmd.exe") { return "Cmd" }
    return "Other"
}

$hits = New-Object System.Collections.Generic.List[object]
$all = Get-ScheduledTask
foreach ($t in $all) {
    try {
        $xml = [xml](Export-ScheduledTask -TaskName $t.TaskName -TaskPath $t.TaskPath -ErrorAction Stop)
        $ns = New-Object System.Xml.XmlNamespaceManager($xml.NameTable)
        $ns.AddNamespace("t", "http://schemas.microsoft.com/windows/2004/02/mit/task")
        $execNodes = $xml.SelectNodes("//t:Exec", $ns)
        if ($execNodes.Count -eq 0) { continue }
        $exec = $execNodes[0]
        $cmdNode = $exec.SelectSingleNode("t:Command", $ns)
        $argNode = $exec.SelectSingleNode("t:Arguments", $ns)
        $cmdStr = if ($cmdNode) { [string]$cmdNode.InnerText } else { "" }
        $argStr = if ($argNode) { [string]$argNode.InnerText } else { "" }
        $fullLine = ($cmdStr + " " + $argStr).Trim()
        if ($fullLine -notmatch [regex]::Escape($workspaceRoot)) { continue }

        $exeBase = Get-ExeBaseName $cmdStr
        $launcher = Get-LauncherBucket $exeBase
        # Match anywhere on the full exec line (covers -WindowStyle on PowerShell / pwsh).
        $hasHidden = [bool]($fullLine -match '(?i)-WindowStyle\s+Hidden')

        $hits.Add([pscustomobject]@{
            TaskPath       = $t.TaskPath
            TaskName       = $t.TaskName
            State          = $t.State
            Execute        = $cmdStr
            Arguments      = $argStr
            Launcher       = $launcher
            HiddenStyleOk  = $hasHidden
        })
    }
    catch {}
}

$outDir = Join-Path $workspaceRoot "reports"
if (-not (Test-Path $outDir)) { New-Item -ItemType Directory -Path $outDir -Force | Out-Null }
$csv = Join-Path $outDir "workspace_scheduled_tasks_audit_latest.csv"
$hits | Export-Csv -NoTypeInformation -Encoding UTF8 $csv
Write-Host "Tasks:" $hits.Count "CSV:" $csv

$missingAny = @($hits | Where-Object { -not $_.HiddenStyleOk })
$missingPs = @($hits | Where-Object { $_.Launcher -eq "PowerShell" -and -not $_.HiddenStyleOk })
$missingDirect = @($hits | Where-Object { $_.Launcher -in @("PythonOrPy", "Cmd") -and -not $_.HiddenStyleOk })
Write-Host "Missing -WindowStyle Hidden (any host):" $missingAny.Count
Write-Host "  PowerShell family still missing Hidden:" $missingPs.Count
Write-Host "  Direct python/py/cmd (no Hidden until wrapped or changed):" $missingDirect.Count
