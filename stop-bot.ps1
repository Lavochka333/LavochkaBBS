param([switch]$Preview)

$botRoot = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot 'dist')) + [IO.Path]::DirectorySeparatorChar
$botProcesses = @(Get-Process xlamBOT -ErrorAction SilentlyContinue | Where-Object {
    $_.Path -and [IO.Path]::GetFullPath($_.Path).StartsWith($botRoot, [StringComparison]::OrdinalIgnoreCase)
})
if ($Preview) {
    $botProcesses | Select-Object Id, Path
    exit 0
}
if (-not $botProcesses.Count) {
    Write-Host 'The bot is already stopped.'
    exit 0
}
$failed = $false
foreach ($botProcess in $botProcesses) {
    try {
        Stop-Process -Id $botProcess.Id -ErrorAction Stop
        Write-Host "Stopped bot $($botProcess.Id)."
    } catch {
        $failed = $true
        Write-Host 'Cannot stop this bot. Run Stop as administrator.'
    }
}
if ($failed) { exit 1 }
