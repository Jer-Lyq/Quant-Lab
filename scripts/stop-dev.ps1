param(
    [int[]]$Ports = @(8000, 5173)
)

$ErrorActionPreference = "Stop"

foreach ($port in $Ports) {
    $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue |
        Where-Object { $_.State -eq "Listen" }

    if (-not $connections) {
        Write-Host "Port $port is not listening."
        continue
    }

    $processIds = $connections |
        Select-Object -ExpandProperty OwningProcess -Unique |
        Where-Object { $_ -and $_ -ne $PID }

    foreach ($processId in $processIds) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            Stop-Process -Id $processId -Force
            Write-Host "Stopped $($process.ProcessName) on port $port (pid $processId)."
        }
    }
}

$Root = Split-Path -Parent $PSScriptRoot
$workerPidFile = Join-Path $Root "logs\backtest-worker.pid"
if (Test-Path -LiteralPath $workerPidFile) {
    $workerId = Get-Content -LiteralPath $workerPidFile -ErrorAction SilentlyContinue
    if ($workerId) {
        $worker = Get-Process -Id $workerId -ErrorAction SilentlyContinue
        if ($worker) {
            Stop-Process -Id $workerId -Force
            Write-Host "Stopped backtest worker (pid $workerId)."
        }
    }
    Remove-Item -LiteralPath $workerPidFile -Force
}
