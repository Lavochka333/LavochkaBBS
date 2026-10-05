param(
    [Parameter(Mandatory = $true)][string]$Program,
    [switch]$Source
)

Set-Location -LiteralPath $PSScriptRoot
$ErrorActionPreference = 'Continue'
$env:PYTHONUNBUFFERED = '1'
$env:PYTHONIOENCODING = 'utf-8:replace'
$env:PYTHONFAULTHANDLER = '1'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
$OutputEncoding = [Console]::OutputEncoding

$logRoot = Join-Path $PSScriptRoot 'logs'
New-Item -ItemType Directory -Path $logRoot -Force -ErrorAction Stop | Out-Null
$logPath = Join-Path $logRoot ("launch-{0}-{1}.log" -f (Get-Date -Format 'yyyyMMdd-HHmmss-fff'), $PID)
$programPath = $ExecutionContext.SessionState.Path.GetUnresolvedProviderPathFromPSPath($Program)
$arguments = @()
if ($Source) {
    # Keep the UI outside the bot process: a native WebView/.NET failure must
    # not take down all device workers with it.
    $arguments = @('-u', '-X', 'faulthandler', (Join-Path $PSScriptRoot 'main.py'), '--web')
}

"Started: $(Get-Date -Format o)" | Tee-Object -FilePath $logPath
"Program: $programPath $($arguments -join ' ')" | Tee-Object -FilePath $logPath -Append
"Log: $logPath" | Tee-Object -FilePath $logPath -Append
$exitCode = 1
try {
    if (-not (Test-Path -LiteralPath $programPath -PathType Leaf)) {
        throw "Program not found: $programPath"
    }
    $global:LASTEXITCODE = 0
    & $programPath @arguments 2>&1 | ForEach-Object { $_.ToString() } | Tee-Object -FilePath $logPath -Append
    $exitCode = $LASTEXITCODE
} catch {
    $_ | Out-String | Tee-Object -FilePath $logPath -Append
}
"Stopped: $(Get-Date -Format o); exit code: $exitCode" | Tee-Object -FilePath $logPath -Append
exit $exitCode
