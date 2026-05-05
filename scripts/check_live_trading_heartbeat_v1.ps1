param(
  [string]$WorkspaceRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path,
  [string]$AppName = "bitcoin-live-small-24h",
  [string]$Symbol = "BTCUSDT",
  [int]$FillHours = 1,
  [int]$FillMaxTrades = 500
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
Set-Location $WorkspaceRoot

function Add-CheckResult {
  param(
    [ref]$List,
    [string]$Name,
    [bool]$Ok,
    [string]$Message
  )
  $List.Value += [ordered]@{
    name = $Name
    ok = $Ok
    message = $Message
  }
}

function Run-CmdCapture {
  param(
    [string]$FilePath,
    [string[]]$Args,
    [int]$TimeoutSeconds = 30
  )
  $psi = [System.Diagnostics.ProcessStartInfo]::new()
  $psi.FileName = $FilePath
  $psi.UseShellExecute = $false
  $psi.RedirectStandardOutput = $true
  $psi.RedirectStandardError = $true
  foreach ($a in $Args) { [void]$psi.ArgumentList.Add($a) }
  $p = [System.Diagnostics.Process]::new()
  $p.StartInfo = $psi
  try {
    [void]$p.Start()
  } catch {
    return @{
      output = "start_failed: $($_.Exception.Message)"
      exit_code = 127
      timed_out = $false
    }
  }
  $waited = $p.WaitForExit($TimeoutSeconds * 1000)
  if (-not $waited) {
    try { $p.Kill($true) } catch { }
    return @{
      output = "timeout_after_${TimeoutSeconds}s"
      exit_code = 124
      timed_out = $true
    }
  }
  $stdout = $p.StandardOutput.ReadToEnd()
  $stderr = $p.StandardError.ReadToEnd()
  $out = ($stdout + $(if ($stderr) { "`n" + $stderr } else { "" })).Trim()
  $code = $p.ExitCode
  return @{
    output = [string]$out
    exit_code = [int]$code
    timed_out = $false
  }
}

$results = @()

# 1) pm2 list
$pm2List = Run-CmdCapture -FilePath "pm2" -Args @("list") -TimeoutSeconds 20
if ($pm2List.exit_code -eq 0) {
  Add-CheckResult -List ([ref]$results) -Name "pm2_list" -Ok $true -Message "pm2 list ok"
} else {
  Add-CheckResult -List ([ref]$results) -Name "pm2_list" -Ok $false -Message ("pm2 list failed: " + $pm2List.output)
}

# 2) pm2 show app
$pm2Show = Run-CmdCapture -FilePath "pm2" -Args @("show", $AppName) -TimeoutSeconds 20
$pm2ShowOk = $false
if ($pm2Show.exit_code -eq 0) {
  $txt = $pm2Show.output
  if ($txt -match "(?im)status\s*:?\s*online" -or $txt -match "(?im)\bonline\b") {
    $pm2ShowOk = $true
  }
  Add-CheckResult -List ([ref]$results) -Name "pm2_show" -Ok $pm2ShowOk -Message $(if ($pm2ShowOk) { "app appears online" } else { "app show ok but online status not detected" })
} else {
  Add-CheckResult -List ([ref]$results) -Name "pm2_show" -Ok $false -Message ("pm2 show failed: " + $pm2Show.output)
}

# 3) pm2 logs lines
$pm2Logs = Run-CmdCapture -FilePath "pm2" -Args @("logs", $AppName, "--lines", "80", "--nostream") -TimeoutSeconds 15
if ($pm2Logs.exit_code -eq 0) {
  $hasBody = ($pm2Logs.output.Trim().Length -gt 0)
  Add-CheckResult -List ([ref]$results) -Name "pm2_logs" -Ok $hasBody -Message $(if ($hasBody) { "recent logs fetched" } else { "logs command ok but no content" })
} else {
  Add-CheckResult -List ([ref]$results) -Name "pm2_logs" -Ok $false -Message ("pm2 logs failed: " + $pm2Logs.output)
}

# 4) GO/NO_GO rebuild
$goNoGoScript = Join-Path $WorkspaceRoot "scripts\build_trading_go_nogo_status_v1.py"
$goNoGo = Run-CmdCapture -FilePath "py" -Args @($goNoGoScript) -TimeoutSeconds 20
if ($goNoGo.exit_code -eq 0) {
  Add-CheckResult -List ([ref]$results) -Name "go_no_go" -Ok $true -Message "GO_NO_GO=GO"
} elseif ($goNoGo.exit_code -eq 1) {
  Add-CheckResult -List ([ref]$results) -Name "go_no_go" -Ok $false -Message "GO_NO_GO=NO_GO"
} else {
  Add-CheckResult -List ([ref]$results) -Name "go_no_go" -Ok $false -Message ("build_trading_go_nogo_status_v1.py failed: " + $goNoGo.output)
}

# 5) recent fills export
$fillsOutDir = Join-Path $WorkspaceRoot "reports\binance_usdm_single_order\order_followup"
$fillScript = Join-Path $WorkspaceRoot "projects\bitcoin-trading\scripts\export_binance_fills_to_cursor_trade_history_v1.py"
$fillRun = Run-CmdCapture -FilePath "py" -Args @(
  $fillScript,
  "--symbol", $Symbol,
  "--hours", "$FillHours",
  "--max-trades", "$FillMaxTrades",
  "--out-dir", $fillsOutDir
) -TimeoutSeconds 60
$tradesPath = Join-Path $fillsOutDir "trades_treatment.json"
if ($fillRun.exit_code -eq 0 -and (Test-Path -LiteralPath $tradesPath)) {
  try {
    $rows = Get-Content -LiteralPath $tradesPath -Encoding UTF8 -Raw | ConvertFrom-Json -Depth 20
    $count = @($rows).Count
    Add-CheckResult -List ([ref]$results) -Name "fills_export" -Ok $true -Message ("fills export ok, rows=" + $count)
  } catch {
    Add-CheckResult -List ([ref]$results) -Name "fills_export" -Ok $false -Message "fills export output not valid JSON"
  }
} else {
  Add-CheckResult -List ([ref]$results) -Name "fills_export" -Ok $false -Message ("fills export failed: " + $fillRun.output)
}

$allOk = -not ($results | Where-Object { -not $_.ok })
$summary = [ordered]@{
  schema = "live_trading_heartbeat_v1"
  generated_at_utc = [DateTime]::UtcNow.ToString("o")
  app_name = $AppName
  symbol = $Symbol
  overall = $(if ($allOk) { "PASS" } else { "FAIL" })
  checks = $results
}

$outPath = Join-Path $WorkspaceRoot "reports\live_trading_heartbeat_latest.json"
$summaryJson = $summary | ConvertTo-Json -Depth 10
[IO.File]::WriteAllText($outPath, "$summaryJson`n", [Text.UTF8Encoding]::new($false))

Write-Host ("HEARTBEAT: " + $summary.overall)
Write-Host ("REPORT: " + $outPath)
foreach ($c in $results) {
  Write-Host (" - [{0}] {1}: {2}" -f $(if ($c.ok) { "OK" } else { "FAIL" }), $c.name, $c.message)
}

if ($allOk) { exit 0 } else { exit 1 }

