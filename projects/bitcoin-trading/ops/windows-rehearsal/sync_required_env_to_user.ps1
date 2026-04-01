$ErrorActionPreference = "Stop"

$envFile = "C:\workspace\.env"
$keys = @(
  "BINANCE_API_KEY",
  "BINANCE_API_SECRET",
  "PUBLIC_EVENT_BRIDGE_WEBHOOK_URL",
  "PUBLIC_EVENT_BRIDGE_TOKEN",
  "PUBLIC_EVENT_GATEWAY_TOKEN"
)

if (-not (Test-Path -LiteralPath $envFile)) {
  throw "Missing .env file: $envFile"
}

$map = @{}
Get-Content -LiteralPath $envFile | ForEach-Object {
  $line = $_.Trim()
  if (-not $line -or $line.StartsWith("#") -or $line.IndexOf("=") -lt 1) {
    return
  }
  $idx = $line.IndexOf("=")
  $k = $line.Substring(0, $idx).Trim()
  $v = $line.Substring($idx + 1)
  $map[$k] = $v
}

foreach ($k in $keys) {
  if ($map.ContainsKey($k) -and -not [string]::IsNullOrWhiteSpace($map[$k])) {
    [Environment]::SetEnvironmentVariable($k, $map[$k], "User")
    Write-Host "SET_USER:$k"
  }
  else {
    Write-Host "SKIP_MISSING_IN_DOTENV:$k"
  }
}

foreach ($k in $keys) {
  $uv = [Environment]::GetEnvironmentVariable($k, "User")
  if ([string]::IsNullOrWhiteSpace($uv)) {
    Write-Host "USER_MISSING:$k"
  }
  else {
    Write-Host "USER_OK:$k"
  }
}

